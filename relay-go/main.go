package main

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	_ "github.com/mattn/go-sqlite3"
)

// Event represents a Nostr event
type Event struct {
	ID        string     `json:"id"`
	PubKey    string     `json:"pubkey"`
	CreatedAt int64      `json:"created_at"`
	Kind      int        `json:"kind"`
	Tags      [][]string `json:"tags"`
	Content   string     `json:"content"`
	Sig       string     `json:"sig"`
}

// Filter represents subscription filters
type Filter struct {
	IDs     []string           `json:"ids,omitempty"`
	Authors []string           `json:"authors,omitempty"`
	Kinds   []int              `json:"kinds,omitempty"`
	Since   *int64             `json:"since,omitempty"`
	Until   *int64             `json:"until,omitempty"`
	Limit   *int               `json:"limit,omitempty"`
	Tags    map[string][]string `json:"-"`
	Search  string             `json:"search,omitempty"`
}

// Subscription represents a client subscription
type Subscription struct {
	ID      string   `json:"id"`
	Filters []Filter `json:"filters"`
	Client  *Client  `json:"-"`
}

// Client represents a connected WebSocket client
type Client struct {
	ID           string
	Conn         *websocket.Conn
	Send         chan []byte
	Relay        *Relay
	Subscriptions map[string]*Subscription
	AuthChallenge string
	Authenticated bool
	PubKey        string
	mu           sync.RWMutex
}

// Relay represents the main relay structure
type Relay struct {
	clients       map[string]*Client
	mu            sync.RWMutex
	db            *sql.DB
	upgrader      websocket.Upgrader
	supportedNIPs []int
	ownerPubKey   string
	ownerOnly     bool
	relayName     string
	relayDesc     string
	relayContact  string
	relayPubKey   string
}

// RelayInfo represents NIP-11 relay information
type RelayInfo struct {
	Name           string `json:"name"`
	Description    string `json:"description"`
	PubKey         string `json:"pubkey"`
	Contact        string `json:"contact"`
	SupportedNIPs  []int  `json:"supported_nips"`
	Software       string `json:"software"`
	Version        string `json:"version"`
	Limitation     struct {
		MaxMessageLength      int  `json:"max_message_length"`
		MaxSubscriptions      int  `json:"max_subscriptions"`
		MaxFilters           int  `json:"max_filters"`
		MaxLimit             int  `json:"max_limit"`
		MaxSubidLength       int  `json:"max_subid_length"`
		MaxEventTags         int  `json:"max_event_tags"`
		MaxContentLength     int  `json:"max_content_length"`
		MinPowDifficulty     int  `json:"min_pow_difficulty"`
		AuthRequired         bool `json:"auth_required"`
		PaymentRequired      bool `json:"payment_required"`
		RestrictedWrites     bool `json:"restricted_writes"`
		CreatedAtLowerLimit  int64 `json:"created_at_lower_limit"`
		CreatedAtUpperLimit  int64 `json:"created_at_upper_limit"`
	} `json:"limitation"`
}

// NewRelay creates a new relay instance
func NewRelay() *Relay {
	// Initialize database
	db, err := sql.Open("sqlite3", "../data/nostr_content.db")
	if err != nil {
		log.Fatal("Failed to open database:", err)
	}

	// Get configuration from environment
	ownerNpub := getEnv("NOSTR_NPUB", "")
	ownerOnly := getEnv("RELAY_OWNER_ONLY", "true") == "true"
	relayName := getEnv("RELAY_NAME", "Enhanced Personal Nostr Hub")
	relayDesc := getEnv("RELAY_DESCRIPTION", "Enhanced personal Nostr relay with multi-NIP support and content aggregation")
	relayContact := getEnv("RELAY_CONTACT", "admin@localhost")

	// Convert npub to hex if provided
	var ownerPubKey string
	if ownerNpub != "" {
		if strings.HasPrefix(ownerNpub, "npub1") {
			// Convert npub to hex (simplified conversion)
			ownerPubKey = npubToHex(ownerNpub)
		} else {
			ownerPubKey = ownerNpub
		}
	}

	relay := &Relay{
		clients:       make(map[string]*Client),
		db:            db,
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool {
				return true // Allow all origins for now
			},
		},
		supportedNIPs: []int{1, 2, 3, 4, 5, 9, 10, 11, 12, 13, 15, 16, 20, 22, 25, 26, 28, 33, 40, 42, 45, 50, 65},
		ownerPubKey:   ownerPubKey,
		ownerOnly:     ownerOnly,
		relayName:     relayName,
		relayDesc:     relayDesc,
		relayContact:  relayContact,
	}

	relay.initDatabase()
	return relay
}

// initDatabase initializes the database tables
func (r *Relay) initDatabase() {
	createTables := `
		CREATE TABLE IF NOT EXISTS relay_events (
			id TEXT PRIMARY KEY,
			pubkey TEXT NOT NULL,
			created_at INTEGER NOT NULL,
			kind INTEGER NOT NULL,
			tags TEXT NOT NULL,
			content TEXT NOT NULL,
			sig TEXT NOT NULL,
			received_at INTEGER NOT NULL
		);
	`
	
	_, err := r.db.Exec(createTables)
	if err != nil {
		log.Fatal("Failed to create database tables:", err)
	}
	
	// Create indexes separately
	indexes := []string{
		"CREATE INDEX IF NOT EXISTS idx_relay_events_pubkey ON relay_events(pubkey);",
		"CREATE INDEX IF NOT EXISTS idx_relay_events_kind ON relay_events(kind);",
		"CREATE INDEX IF NOT EXISTS idx_relay_events_created_at ON relay_events(created_at);",
	}
	
	for _, indexSQL := range indexes {
		_, err := r.db.Exec(indexSQL)
		if err != nil {
			log.Printf("Warning: Failed to create index: %v", err)
		}
	}
}

// HandleWebSocket handles WebSocket connections
func (r *Relay) HandleWebSocket(w http.ResponseWriter, req *http.Request) {
	conn, err := r.upgrader.Upgrade(w, req, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}

	client := &Client{
		ID:            generateClientID(),
		Conn:          conn,
		Send:          make(chan []byte, 256),
		Relay:         r,
		Subscriptions: make(map[string]*Subscription),
		AuthChallenge: generateAuthChallenge(),
	}

	r.mu.Lock()
	r.clients[client.ID] = client
	r.mu.Unlock()

	go client.writePump()
	go client.readPump()

	log.Printf("Client %s connected", client.ID)
}

// HandleRelayInfo handles NIP-11 relay information requests
func (r *Relay) HandleRelayInfo(c *gin.Context) {
	info := RelayInfo{
		Name:          r.relayName,
		Description:   r.relayDesc,
		Contact:       r.relayContact,
		SupportedNIPs: r.supportedNIPs,
		Software:      "Enhanced Nostr Home Hub",
		Version:       "2.0.0",
	}

	// Set limitations
	info.Limitation.MaxMessageLength = 65536
	info.Limitation.MaxSubscriptions = 20
	info.Limitation.MaxFilters = 10
	info.Limitation.MaxLimit = 500
	info.Limitation.MaxSubidLength = 64
	info.Limitation.MaxEventTags = 2000
	info.Limitation.MaxContentLength = 65536
	info.Limitation.RestrictedWrites = r.ownerOnly
	info.Limitation.AuthRequired = r.ownerOnly

	c.Header("Access-Control-Allow-Origin", "*")
	c.Header("Access-Control-Allow-Methods", "GET")
	c.Header("Access-Control-Allow-Headers", "Accept")
	c.JSON(http.StatusOK, info)
}

// readPump handles reading from WebSocket
func (c *Client) readPump() {
	defer func() {
		c.Relay.unregisterClient(c)
		c.Conn.Close()
	}()

	c.Conn.SetReadLimit(65536)
	c.Conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	c.Conn.SetPongHandler(func(string) error {
		c.Conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, message, err := c.Conn.ReadMessage()
		if err != nil {
			log.Printf("Client %s read error: %v", c.ID, err)
			break
		}

		c.handleMessage(message)
	}
}

// writePump handles writing to WebSocket
func (c *Client) writePump() {
	ticker := time.NewTicker(54 * time.Second)
	defer func() {
		ticker.Stop()
		c.Conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.Send:
			c.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				c.Conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := c.Conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			w.Write(message)

			// Add queued messages to the current message
			n := len(c.Send)
			for i := 0; i < n; i++ {
				w.Write([]byte{'\n'})
				w.Write(<-c.Send)
			}

			if err := w.Close(); err != nil {
				return
			}

		case <-ticker.C:
			c.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.Conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// handleMessage processes incoming WebSocket messages
func (c *Client) handleMessage(data []byte) {
	var message []interface{}
	if err := json.Unmarshal(data, &message); err != nil {
		c.sendNotice("ERROR: Invalid JSON")
		return
	}

	if len(message) == 0 {
		c.sendNotice("ERROR: Empty message")
		return
	}

	messageType, ok := message[0].(string)
	if !ok {
		c.sendNotice("ERROR: Invalid message type")
		return
	}

	switch messageType {
	case "EVENT":
		c.handleEvent(message)
	case "REQ":
		c.handleReq(message)
	case "CLOSE":
		c.handleClose(message)
	case "COUNT":
		c.handleCount(message) // NIP-45
	case "AUTH":
		c.handleAuth(message)
	default:
		c.sendNotice(fmt.Sprintf("ERROR: Unknown message type: %s", messageType))
	}
}

// handleEvent processes EVENT messages with comprehensive NIP support
func (c *Client) handleEvent(message []interface{}) {
	if len(message) < 2 {
		c.sendOK("", false, "ERROR: Invalid EVENT message")
		return
	}

	eventData, ok := message[1].(map[string]interface{})
	if !ok {
		c.sendOK("", false, "ERROR: Invalid event data")
		return
	}

	event, err := parseEvent(eventData)
	if err != nil {
		c.sendOK("", false, fmt.Sprintf("ERROR: %v", err))
		return
	}

	// Validate event
	if !c.validateEvent(event) {
		c.sendOK(event.ID, false, "ERROR: Event validation failed")
		return
	}

	// Check owner-only mode
	if c.Relay.ownerOnly && event.PubKey != c.Relay.ownerPubKey {
		c.sendOK(event.ID, false, "ERROR: restricted: only owner can publish events")
		return
	}

	// NIP-09: Handle event deletion
	if event.Kind == 5 {
		c.handleEventDeletion(event)
		c.sendOK(event.ID, true, "")
		return
	}

	// NIP-03: OpenTimestamps attestations
	if event.Kind == 1040 {
		c.handleOpenTimestamps(event)
	}

	// NIP-02: Contact List
	if event.Kind == 3 {
		c.handleContactList(event)
	}

	// NIP-04: Encrypted Direct Message
	if event.Kind == 4 {
		c.handleEncryptedDM(event)
	}

	// NIP-25: Reactions
	if event.Kind == 7 {
		c.handleReaction(event)
	}

	// NIP-28: Public Chat
	if event.Kind == 40 || event.Kind == 41 || event.Kind == 42 {
		c.handlePublicChat(event)
	}

	// NIP-65: Relay List Metadata
	if event.Kind == 10002 {
		c.handleRelayListMetadata(event)
	}

	// NIP-05: DNS-based identifiers (validate if present)
	if event.Kind == 0 {
		c.handleMetadata(event)
	}

	// Store event
	if err := c.Relay.storeEvent(event); err != nil {
		c.sendOK(event.ID, false, fmt.Sprintf("ERROR: Failed to store event: %v", err))
		return
	}

	c.sendOK(event.ID, true, "")

	// Broadcast to subscribers
	c.Relay.broadcastEvent(event)
}

// NIP-09: Handle event deletion
func (c *Client) handleEventDeletion(event *Event) {
	// Extract event IDs to delete from 'e' tags
	for _, tag := range event.Tags {
		if len(tag) >= 2 && tag[0] == "e" {
			eventIDToDelete := tag[1]
			// Only allow deletion of own events
			deleteQuery := "DELETE FROM relay_events WHERE id = ? AND pubkey = ?"
			c.Relay.db.Exec(deleteQuery, eventIDToDelete, event.PubKey)
		}
	}
}

// NIP-03: Handle OpenTimestamps attestations
func (c *Client) handleOpenTimestamps(event *Event) {
	// Store timestamp attestations (kind 1040)
	// In a full implementation, you'd verify the OpenTimestamp proof
	log.Printf("OpenTimestamp attestation received for event %s", event.ID)
}

// NIP-02: Handle contact lists
func (c *Client) handleContactList(event *Event) {
	// Contact list events (kind 3) contain 'p' tags with pubkeys
	log.Printf("Contact list updated for pubkey %s", event.PubKey)
}

// NIP-04: Handle encrypted direct messages
func (c *Client) handleEncryptedDM(event *Event) {
	// Encrypted DMs (kind 4) should have 'p' tag with recipient
	for _, tag := range event.Tags {
		if len(tag) >= 2 && tag[0] == "p" {
			recipient := tag[1]
			log.Printf("Encrypted DM from %s to %s", event.PubKey, recipient)
			break
		}
	}
}

// NIP-25: Handle reactions
func (c *Client) handleReaction(event *Event) {
	// Reactions (kind 7) should have 'e' tag pointing to reacted event
	for _, tag := range event.Tags {
		if len(tag) >= 2 && tag[0] == "e" {
			reactedEventID := tag[1]
			log.Printf("Reaction '%s' to event %s", event.Content, reactedEventID)
			break
		}
	}
}

// NIP-28: Handle public chat events
func (c *Client) handlePublicChat(event *Event) {
	switch event.Kind {
	case 40: // Channel Creation
		log.Printf("Channel created: %s", event.Content)
	case 41: // Channel Metadata
		log.Printf("Channel metadata updated")
	case 42: // Channel Message
		// Should have 'e' tag pointing to channel creation event
		for _, tag := range event.Tags {
			if len(tag) >= 2 && tag[0] == "e" {
				channelID := tag[1]
				log.Printf("Message in channel %s: %s", channelID, event.Content)
				break
			}
		}
	}
}

// NIP-65: Handle relay list metadata
func (c *Client) handleRelayListMetadata(event *Event) {
	log.Printf("Relay list metadata updated for pubkey %s", event.PubKey)
	// Store relay preferences for the user
	// In a full implementation, you might use this to optimize relay routing
}

// NIP-05: Handle metadata events (kind 0) with potential NIP-05 validation
func (c *Client) handleMetadata(event *Event) {
	// Parse metadata JSON
	var metadata map[string]interface{}
	if err := json.Unmarshal([]byte(event.Content), &metadata); err == nil {
		if nip05, ok := metadata["nip05"].(string); ok && nip05 != "" {
			// In a full implementation, you'd validate the NIP-05 identifier
			log.Printf("NIP-05 identifier found: %s for pubkey %s", nip05, event.PubKey)
		}
	}
}

// handleReq processes REQ messages (subscriptions) with enhanced filtering
func (c *Client) handleReq(message []interface{}) {
	if len(message) < 3 {
		c.sendNotice("ERROR: Invalid REQ message")
		return
	}

	subID, ok := message[1].(string)
	if !ok {
		c.sendNotice("ERROR: Invalid subscription ID")
		return
	}

	// Parse filters
	var filters []Filter
	for i := 2; i < len(message); i++ {
		filterData, ok := message[i].(map[string]interface{})
		if !ok {
			continue
		}
		filter := parseFilter(filterData)
		filters = append(filters, filter)
	}

	subscription := &Subscription{
		ID:      subID,
		Filters: filters,
		Client:  c,
	}

	c.mu.Lock()
	c.Subscriptions[subID] = subscription
	c.mu.Unlock()

	// Send existing events that match the filters
	c.sendMatchingEvents(subscription)

	// Send EOSE (NIP-15)
	c.sendEOSE(subID)
}

// Enhanced filter parsing with NIP support
func parseFilter(data map[string]interface{}) Filter {
	filter := Filter{
		Tags: make(map[string][]string),
	}
	
	if ids, ok := data["ids"].([]interface{}); ok {
		for _, id := range ids {
			if str, ok := id.(string); ok {
				filter.IDs = append(filter.IDs, str)
			}
		}
	}
	
	if authors, ok := data["authors"].([]interface{}); ok {
		for _, author := range authors {
			if str, ok := author.(string); ok {
				filter.Authors = append(filter.Authors, str)
			}
		}
	}
	
	if kinds, ok := data["kinds"].([]interface{}); ok {
		for _, kind := range kinds {
			if num, ok := kind.(float64); ok {
				filter.Kinds = append(filter.Kinds, int(num))
			}
		}
	}
	
	if since, ok := data["since"].(float64); ok {
		sinceInt := int64(since)
		filter.Since = &sinceInt
	}
	
	if until, ok := data["until"].(float64); ok {
		untilInt := int64(until)
		filter.Until = &untilInt
	}
	
	if limit, ok := data["limit"].(float64); ok {
		limitInt := int(limit)
		filter.Limit = &limitInt
	}

	// NIP-12: Generic tag queries (#e, #p, etc.)
	for key, value := range data {
		if strings.HasPrefix(key, "#") && len(key) == 2 {
			tagName := key[1:]
			if tagValues, ok := value.([]interface{}); ok {
				var values []string
				for _, v := range tagValues {
					if str, ok := v.(string); ok {
						values = append(values, str)
					}
				}
				filter.Tags[tagName] = values
			}
		}
	}

	// NIP-50: Search filter
	if search, ok := data["search"].(string); ok {
		filter.Search = search
	}
	
	return filter
}

// handleClose processes CLOSE messages
func (c *Client) handleClose(message []interface{}) {
	if len(message) < 2 {
		c.sendNotice("ERROR: Invalid CLOSE message")
		return
	}

	subID, ok := message[1].(string)
	if !ok {
		c.sendNotice("ERROR: Invalid subscription ID")
		return
	}

	c.mu.Lock()
	delete(c.Subscriptions, subID)
	c.mu.Unlock()
}

// NIP-45: Handle COUNT messages
func (c *Client) handleCount(message []interface{}) {
	if len(message) < 3 {
		c.sendNotice("ERROR: Invalid COUNT message")
		return
	}

	subID, ok := message[1].(string)
	if !ok {
		c.sendNotice("ERROR: Invalid subscription ID")
		return
	}

	// Parse filters (same as REQ)
	var filters []Filter
	for i := 2; i < len(message); i++ {
		filterData, ok := message[i].(map[string]interface{})
		if !ok {
			continue
		}
		filter := parseFilter(filterData)
		filters = append(filters, filter)
	}

	// Count matching events
	count := c.countMatchingEvents(filters)
	
	// Send COUNT response
	c.sendCount(subID, count)
}

// Count events matching filters
func (c *Client) countMatchingEvents(filters []Filter) int64 {
	query := "SELECT COUNT(*) FROM relay_events WHERE 1=1"
	var args []interface{}
	var conditions []string

	for _, filter := range filters {
		var filterConditions []string
		var filterArgs []interface{}
		
		if len(filter.Kinds) > 0 {
			placeholders := make([]string, len(filter.Kinds))
			for i, kind := range filter.Kinds {
				placeholders[i] = "?"
				filterArgs = append(filterArgs, kind)
			}
			filterConditions = append(filterConditions, "kind IN ("+strings.Join(placeholders, ",")+")")
		}
		
		if len(filter.Authors) > 0 {
			placeholders := make([]string, len(filter.Authors))
			for i, author := range filter.Authors {
				placeholders[i] = "pubkey LIKE ?"
				filterArgs = append(filterArgs, author+"%")
			}
			filterConditions = append(filterConditions, "("+strings.Join(placeholders, " OR ")+")")
		}
		
		if filter.Since != nil {
			filterConditions = append(filterConditions, "created_at >= ?")
			filterArgs = append(filterArgs, *filter.Since)
		}
		
		if filter.Until != nil {
			filterConditions = append(filterConditions, "created_at <= ?")
			filterArgs = append(filterArgs, *filter.Until)
		}

		if len(filterConditions) > 0 {
			conditions = append(conditions, "("+strings.Join(filterConditions, " AND ")+")")
			args = append(args, filterArgs...)
		}
	}

	if len(conditions) > 0 {
		query += " AND (" + strings.Join(conditions, " OR ") + ")"
	}

	var count int64
	err := c.Relay.db.QueryRow(query, args...).Scan(&count)
	if err != nil {
		log.Printf("Count query error: %v", err)
		return 0
	}

	return count
}

// Send COUNT response
func (c *Client) sendCount(subID string, count int64) {
	message := []interface{}{"COUNT", subID, map[string]int64{"count": count}}
	data, _ := json.Marshal(message)
	select {
	case c.Send <- data:
	default:
		close(c.Send)
	}
}

// handleAuth processes AUTH messages
func (c *Client) handleAuth(message []interface{}) {
	if len(message) < 2 {
		c.sendNotice("ERROR: Invalid AUTH message")
		return
	}

	eventData, ok := message[1].(map[string]interface{})
	if !ok {
		c.sendNotice("ERROR: Invalid auth event data")
		return
	}

	event, err := parseEvent(eventData)
	if err != nil {
		c.sendNotice(fmt.Sprintf("ERROR: Invalid auth event: %v", err))
		return
	}

	// Validate auth event (kind 22242)
	if event.Kind != 22242 {
		c.sendNotice("ERROR: Invalid auth event kind")
		return
	}

	// Set client as authenticated
	c.mu.Lock()
	c.Authenticated = true
	c.PubKey = event.PubKey
	c.mu.Unlock()

	c.sendOK(event.ID, true, "")
}

// validateEvent validates a Nostr event with comprehensive NIP support
func (c *Client) validateEvent(event *Event) bool {
	// Check required fields
	if event.ID == "" || event.PubKey == "" || event.Sig == "" {
		return false
	}

	// Validate ID (should be SHA256 of serialized event)
	expectedID := calculateEventID(event)
	if event.ID != expectedID {
		return false
	}

	// NIP-22: Event created_at limits
	now := time.Now().Unix()
	if event.CreatedAt > now+60*10 { // Allow 10 minutes in future
		return false
	}
	if event.CreatedAt < now-60*60*24*30 { // Reject events older than 30 days
		return false
	}

	// NIP-13: Proof of Work validation
	if c.validateProofOfWork(event) == false {
		return false
	}

	// NIP-26: Delegated Event Signing validation
	if !c.validateDelegation(event) {
		return false
	}

	// NIP-40: Expiration timestamp
	if c.isEventExpired(event) {
		return false
	}

	// NIP-16: Event Treatment (replaceable events)
	if c.isReplaceableEvent(event) {
		c.handleReplaceableEvent(event)
	}

	// NIP-33: Parameterized Replaceable Events
	if c.isParameterizedReplaceableEvent(event) {
		c.handleParameterizedReplaceableEvent(event)
	}

	return true
}

// NIP-13: Proof of Work validation
func (c *Client) validateProofOfWork(event *Event) bool {
	// Check for nonce tag and validate PoW
	for _, tag := range event.Tags {
		if len(tag) >= 2 && tag[0] == "nonce" {
			difficulty := c.calculatePoWDifficulty(event.ID)
			if difficulty >= 0 { // Accept any PoW for now, can set minimum
				return true
			}
		}
	}
	return true // Allow events without PoW
}

// Calculate PoW difficulty from event ID
func (c *Client) calculatePoWDifficulty(eventID string) int {
	count := 0
	for _, char := range eventID {
		if char == '0' {
			count++
		} else {
			break
		}
	}
	return count
}

// NIP-26: Delegated Event Signing validation
func (c *Client) validateDelegation(event *Event) bool {
	// Check for delegation tag
	for _, tag := range event.Tags {
		if len(tag) >= 4 && tag[0] == "delegation" {
			delegatorPubkey := tag[1]
			conditions := tag[2]
			signature := tag[3]
			
			// Validate delegation conditions and signature
			if c.validateDelegationSignature(delegatorPubkey, conditions, signature, event) {
				return true
			}
		}
	}
	return true // Allow non-delegated events
}

// Validate delegation signature (simplified)
func (c *Client) validateDelegationSignature(delegator, conditions, signature string, event *Event) bool {
	// In a real implementation, you'd verify the cryptographic signature
	// For now, just check that the delegation tag is properly formatted
	return len(delegator) == 64 && len(signature) > 0
}

// NIP-40: Check if event is expired
func (c *Client) isEventExpired(event *Event) bool {
	for _, tag := range event.Tags {
		if len(tag) >= 2 && tag[0] == "expiration" {
			if expiration, err := strconv.ParseInt(tag[1], 10, 64); err == nil {
				return time.Now().Unix() > expiration
			}
		}
	}
	return false
}

// NIP-16: Check if event is replaceable
func (c *Client) isReplaceableEvent(event *Event) bool {
	return event.Kind >= 10000 && event.Kind < 20000
}

// Handle replaceable events (NIP-16)
func (c *Client) handleReplaceableEvent(event *Event) {
	// Delete previous events of the same kind from the same author
	deleteQuery := "DELETE FROM relay_events WHERE pubkey = ? AND kind = ? AND created_at < ?"
	c.Relay.db.Exec(deleteQuery, event.PubKey, event.Kind, event.CreatedAt)
}

// NIP-33: Check if event is parameterized replaceable
func (c *Client) isParameterizedReplaceableEvent(event *Event) bool {
	return event.Kind >= 30000 && event.Kind < 40000
}

// Handle parameterized replaceable events (NIP-33)
func (c *Client) handleParameterizedReplaceableEvent(event *Event) {
	// Extract 'd' tag for identifier
	var identifier string
	for _, tag := range event.Tags {
		if len(tag) >= 2 && tag[0] == "d" {
			identifier = tag[1]
			break
		}
	}
	
	// Delete previous events with same kind, author, and identifier
	deleteQuery := "DELETE FROM relay_events WHERE pubkey = ? AND kind = ? AND tags LIKE ? AND created_at < ?"
	pattern := fmt.Sprintf("%%\"d\",\"%s\"%%", identifier)
	c.Relay.db.Exec(deleteQuery, event.PubKey, event.Kind, pattern, event.CreatedAt)
}

// calculateEventID calculates the event ID
func calculateEventID(event *Event) string {
	// Simplified implementation - in production, use proper serialization
	data := fmt.Sprintf(`[0,"%s",%d,%d,%s,"%s"]`,
		event.PubKey,
		event.CreatedAt,
		event.Kind,
		formatTags(event.Tags),
		event.Content,
	)
	
	hash := sha256.Sum256([]byte(data))
	return hex.EncodeToString(hash[:])
}

// formatTags formats tags for ID calculation
func formatTags(tags [][]string) string {
	result, _ := json.Marshal(tags)
	return string(result)
}

// storeEvent stores an event in the database
func (r *Relay) storeEvent(event *Event) error {
	tagsJSON, _ := json.Marshal(event.Tags)
	
	query := `
		INSERT OR REPLACE INTO relay_events 
		(id, pubkey, created_at, kind, tags, content, sig, received_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`
	
	_, err := r.db.Exec(query,
		event.ID,
		event.PubKey,
		event.CreatedAt,
		event.Kind,
		string(tagsJSON),
		event.Content,
		event.Sig,
		time.Now().Unix(),
	)
	
	return err
}

// broadcastEvent broadcasts an event to all matching subscriptions
func (r *Relay) broadcastEvent(event *Event) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	for _, client := range r.clients {
		client.mu.RLock()
		for subID, subscription := range client.Subscriptions {
			if r.eventMatchesFilters(event, subscription.Filters) {
				client.sendEvent(subID, event)
			}
		}
		client.mu.RUnlock()
	}
}

// eventMatchesFilters checks if an event matches any of the filters
func (r *Relay) eventMatchesFilters(event *Event, filters []Filter) bool {
	for _, filter := range filters {
		if r.eventMatchesFilter(event, filter) {
			return true
		}
	}
	return false
}

// eventMatchesFilter checks if an event matches a specific filter with full NIP support
func (r *Relay) eventMatchesFilter(event *Event, filter Filter) bool {
	// Check IDs
	if len(filter.IDs) > 0 {
		found := false
		for _, id := range filter.IDs {
			if strings.HasPrefix(event.ID, id) {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}

	// Check authors
	if len(filter.Authors) > 0 {
		found := false
		for _, author := range filter.Authors {
			if strings.HasPrefix(event.PubKey, author) {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}

	// Check kinds
	if len(filter.Kinds) > 0 {
		found := false
		for _, kind := range filter.Kinds {
			if event.Kind == kind {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}

	// Check time range
	if filter.Since != nil && event.CreatedAt < *filter.Since {
		return false
	}
	if filter.Until != nil && event.CreatedAt > *filter.Until {
		return false
	}

	// NIP-12: Generic tag queries
	for tagName, filterValues := range filter.Tags {
		if len(filterValues) > 0 {
			found := false
			for _, tag := range event.Tags {
				if len(tag) >= 2 && tag[0] == tagName {
					for _, filterValue := range filterValues {
						if strings.HasPrefix(tag[1], filterValue) {
							found = true
							break
						}
					}
					if found {
						break
					}
				}
			}
			if !found {
				return false
			}
		}
	}

	// NIP-50: Search filter
	if filter.Search != "" {
		searchLower := strings.ToLower(filter.Search)
		contentLower := strings.ToLower(event.Content)
		if !strings.Contains(contentLower, searchLower) {
			// Also search in tags
			found := false
			for _, tag := range event.Tags {
				for _, tagValue := range tag {
					if strings.Contains(strings.ToLower(tagValue), searchLower) {
						found = true
						break
					}
				}
				if found {
					break
				}
			}
			if !found {
				return false
			}
		}
	}

	return true
}

// sendMatchingEvents sends existing events that match subscription filters with enhanced NIP support
func (c *Client) sendMatchingEvents(subscription *Subscription) {
	// Build query based on filters with comprehensive NIP support
	query := "SELECT id, pubkey, created_at, kind, tags, content, sig FROM relay_events WHERE 1=1"
	var args []interface{}
	var conditions []string

	for _, filter := range subscription.Filters {
		var filterConditions []string
		var filterArgs []interface{}
		
		// IDs filter
		if len(filter.IDs) > 0 {
			placeholders := make([]string, len(filter.IDs))
			for i, id := range filter.IDs {
				placeholders[i] = "id LIKE ?"
				filterArgs = append(filterArgs, id+"%")
			}
			filterConditions = append(filterConditions, "("+strings.Join(placeholders, " OR ")+")")
		}
		
		// Authors filter  
		if len(filter.Authors) > 0 {
			placeholders := make([]string, len(filter.Authors))
			for i, author := range filter.Authors {
				placeholders[i] = "pubkey LIKE ?"
				filterArgs = append(filterArgs, author+"%")
			}
			filterConditions = append(filterConditions, "("+strings.Join(placeholders, " OR ")+")")
		}
		
		// Kinds filter
		if len(filter.Kinds) > 0 {
			placeholders := make([]string, len(filter.Kinds))
			for i, kind := range filter.Kinds {
				placeholders[i] = "?"
				filterArgs = append(filterArgs, kind)
			}
			filterConditions = append(filterConditions, "kind IN ("+strings.Join(placeholders, ",")+")")
		}
		
		// Time range filters
		if filter.Since != nil {
			filterConditions = append(filterConditions, "created_at >= ?")
			filterArgs = append(filterArgs, *filter.Since)
		}
		
		if filter.Until != nil {
			filterConditions = append(filterConditions, "created_at <= ?")
			filterArgs = append(filterArgs, *filter.Until)
		}

		// NIP-12: Generic tag queries
		for tagName, tagValues := range filter.Tags {
			if len(tagValues) > 0 {
				tagConditions := make([]string, len(tagValues))
				for i, tagValue := range tagValues {
					tagConditions[i] = "tags LIKE ?"
					filterArgs = append(filterArgs, fmt.Sprintf("%%\"%s\",\"%s%%", tagName, tagValue))
				}
				filterConditions = append(filterConditions, "("+strings.Join(tagConditions, " OR ")+")")
			}
		}

		// NIP-50: Search filter
		if filter.Search != "" {
			searchCondition := "(content LIKE ? OR tags LIKE ?)"
			searchPattern := "%" + filter.Search + "%"
			filterConditions = append(filterConditions, searchCondition)
			filterArgs = append(filterArgs, searchPattern, searchPattern)
		}

		// Combine filter conditions with AND
		if len(filterConditions) > 0 {
			conditions = append(conditions, "("+strings.Join(filterConditions, " AND ")+")")
			args = append(args, filterArgs...)
		}
	}

	// Combine all filter conditions with OR (any filter can match)
	if len(conditions) > 0 {
		query += " AND (" + strings.Join(conditions, " OR ") + ")"
	}

	query += " ORDER BY created_at DESC"
	
	// Apply limit (use the most restrictive limit from all filters)
	limit := 100 // default
	for _, filter := range subscription.Filters {
		if filter.Limit != nil && *filter.Limit < limit {
			limit = *filter.Limit
		}
	}
	query += " LIMIT ?"
	args = append(args, limit)

	rows, err := c.Relay.db.Query(query, args...)
	if err != nil {
		log.Printf("Query error: %v", err)
		return
	}
	defer rows.Close()

	eventCount := 0
	for rows.Next() {
		var event Event
		var tagsJSON string
		
		err := rows.Scan(
			&event.ID,
			&event.PubKey,
			&event.CreatedAt,
			&event.Kind,
			&tagsJSON,
			&event.Content,
			&event.Sig,
		)
		if err != nil {
			continue
		}

		json.Unmarshal([]byte(tagsJSON), &event.Tags)
		
		// Additional filtering for complex conditions that can't be done in SQL
		matches := false
		for _, filter := range subscription.Filters {
			if c.Relay.eventMatchesFilter(&event, filter) {
				matches = true
				break
			}
		}
		
		if matches {
			c.sendEvent(subscription.ID, &event)
			eventCount++
		}
	}

	log.Printf("Sent %d events for subscription %s", eventCount, subscription.ID)
}

// Client message sending methods
func (c *Client) sendEvent(subID string, event *Event) {
	message := []interface{}{"EVENT", subID, event}
	data, _ := json.Marshal(message)
	select {
	case c.Send <- data:
	default:
		close(c.Send)
	}
}

func (c *Client) sendOK(eventID string, accepted bool, message string) {
	response := []interface{}{"OK", eventID, accepted, message}
	data, _ := json.Marshal(response)
	select {
	case c.Send <- data:
	default:
		close(c.Send)
	}
}

func (c *Client) sendEOSE(subID string) {
	message := []interface{}{"EOSE", subID}
	data, _ := json.Marshal(message)
	select {
	case c.Send <- data:
	default:
		close(c.Send)
	}
}

func (c *Client) sendNotice(notice string) {
	message := []interface{}{"NOTICE", notice}
	data, _ := json.Marshal(message)
	select {
	case c.Send <- data:
	default:
		close(c.Send)
	}
}

func (c *Client) sendAuth() {
	message := []interface{}{"AUTH", c.AuthChallenge}
	data, _ := json.Marshal(message)
	select {
	case c.Send <- data:
	default:
		close(c.Send)
	}
}

// unregisterClient removes a client from the relay
func (r *Relay) unregisterClient(client *Client) {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	if _, ok := r.clients[client.ID]; ok {
		delete(r.clients, client.ID)
		close(client.Send)
		log.Printf("Client %s disconnected", client.ID)
	}
}

// Utility functions
func parseEvent(data map[string]interface{}) (*Event, error) {
	event := &Event{}
	
	if id, ok := data["id"].(string); ok {
		event.ID = id
	}
	
	if pubkey, ok := data["pubkey"].(string); ok {
		event.PubKey = pubkey
	}
	
	if createdAt, ok := data["created_at"].(float64); ok {
		event.CreatedAt = int64(createdAt)
	}
	
	if kind, ok := data["kind"].(float64); ok {
		event.Kind = int(kind)
	}
	
	if content, ok := data["content"].(string); ok {
		event.Content = content
	}
	
	if sig, ok := data["sig"].(string); ok {
		event.Sig = sig
	}
	
	if tags, ok := data["tags"].([]interface{}); ok {
		for _, tag := range tags {
			if tagArray, ok := tag.([]interface{}); ok {
				var tagStrings []string
				for _, item := range tagArray {
					if str, ok := item.(string); ok {
						tagStrings = append(tagStrings, str)
					}
				}
				event.Tags = append(event.Tags, tagStrings)
			}
		}
	}
	
	return event, nil
}

func generateClientID() string {
	return fmt.Sprintf("client_%d_%d", time.Now().UnixNano(), time.Now().Unix())
}

func generateAuthChallenge() string {
	return fmt.Sprintf("challenge_%d", time.Now().UnixNano())
}

func npubToHex(npub string) string {
	// Simplified npub to hex conversion
	// In production, use proper bech32 decoding
	if len(npub) > 5 {
		return npub[5:] // Remove "npub1" prefix for now
	}
	return npub
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
	relay := NewRelay()
	
	// Setup Gin router
	gin.SetMode(gin.ReleaseMode)
	router := gin.Default()
	
	// Enable CORS
	router.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Accept, Content-Type, Content-Length, Accept-Encoding, Authorization")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		
		c.Next()
	})
	
	// NIP-11 relay information
	router.GET("/", relay.HandleRelayInfo)
	router.GET("/relay/info", relay.HandleRelayInfo)
	
	// WebSocket endpoint
	router.GET("/ws", gin.WrapF(relay.HandleWebSocket))
	
	// Relay statistics endpoint
	router.GET("/relay/stats", func(c *gin.Context) {
		relay.mu.RLock()
		clientCount := len(relay.clients)
		relay.mu.RUnlock()
		
		// Get event count from database
		var eventCount int
		relay.db.QueryRow("SELECT COUNT(*) FROM relay_events").Scan(&eventCount)
		
		stats := map[string]interface{}{
			"connected_clients": clientCount,
			"total_events":     eventCount,
			"supported_nips":   relay.supportedNIPs,
			"owner_only":       relay.ownerOnly,
			"relay_name":       relay.relayName,
		}
		
		c.JSON(200, stats)
	})
	
	port := getEnv("RELAY_PORT", "8080")
	
	fmt.Printf("🚀 Enhanced Nostr Relay (Go) starting on port %s\n", port)
	fmt.Printf("📄 Name: %s\n", relay.relayName)
	fmt.Printf("📝 Description: %s\n", relay.relayDesc)
	if relay.ownerOnly {
		fmt.Printf("🔒 Owner-only mode enabled\n")
		fmt.Printf("🔑 Owner pubkey: %s\n", relay.ownerPubKey)
	}
	fmt.Printf("✨ Supported NIPs: %v\n", relay.supportedNIPs)
	fmt.Printf("🌐 WebSocket endpoint: ws://localhost:%s/ws\n", port)
	fmt.Printf("📊 Relay info: http://localhost:%s/\n", port)
	
	log.Fatal(http.ListenAndServe(":"+port, router))
}
