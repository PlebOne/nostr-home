package main

import (
	"bytes"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
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
	IDs     []string            `json:"ids,omitempty"`
	Authors []string            `json:"authors,omitempty"`
	Kinds   []int               `json:"kinds,omitempty"`
	Since   *int64              `json:"since,omitempty"`
	Until   *int64              `json:"until,omitempty"`
	Limit   *int                `json:"limit,omitempty"`
	Tags    map[string][]string `json:"-"`
	Search  string              `json:"search,omitempty"`
}

// Subscription represents a client subscription
type Subscription struct {
	ID      string   `json:"id"`
	Filters []Filter `json:"filters"`
	Client  *Client  `json:"-"`
}

// Client represents a WebSocket client
type Client struct {
	ID            string
	Conn          *websocket.Conn
	Subscriptions map[string]*Subscription
	Send          chan []byte
	Relay         *Relay
	mu            sync.RWMutex
	lastSeen      time.Time
}

// Relay represents the main relay structure
type Relay struct {
	db           *sql.DB
	clients      map[string]*Client
	clientsMutex sync.RWMutex
	upgrader     websocket.Upgrader
	dataDir      string
	// Add notification settings
	notifyURL    string
	lastNotify   time.Time
	notifyMutex  sync.Mutex
}

var (
	relay *Relay
)

func main() {
	gin.SetMode(gin.ReleaseMode)

	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		dataDir = "/app/data"
	}

	// Initialize relay with notification URL
	notifyURL := os.Getenv("NOTIFY_URL")
	if notifyURL == "" {
		notifyURL = "http://nostr-home:3000/api/update-cache" // Default to docker service name
	}

	var err error
	relay, err = NewRelay(dataDir, notifyURL)
	if err != nil {
		log.Fatalf("Failed to create relay: %v", err)
	}
	defer relay.Close()

	router := gin.Default()

	// Enable CORS
	router.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		
		c.Next()
	})

	// WebSocket endpoint
	router.GET("/ws", handleWebSocket)
	router.GET("/", handleWebSocket)

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok", "clients": len(relay.clients)})
	})

	// Stats endpoint
	router.GET("/stats", func(c *gin.Context) {
		stats := relay.getStats()
		c.JSON(200, stats)
	})

	log.Printf("🚀 Nostr Relay starting on :7447")
	log.Printf("📡 WebSocket endpoint: ws://localhost:7447/ws")
	log.Printf("📊 Stats endpoint: http://localhost:7447/stats")
	log.Printf("📮 Notifications: %s", notifyURL)
	
	log.Fatal(router.Run(":7447"))
}

// NewRelay creates a new relay instance
func NewRelay(dataDir string, notifyURL string) (*Relay, error) {
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create data directory: %v", err)
	}

	dbPath := dataDir + "/relay.db"
	db, err := sql.Open("sqlite3", dbPath+"?_journal_mode=WAL")
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %v", err)
	}

	relay := &Relay{
		db:        db,
		clients:   make(map[string]*Client),
		dataDir:   dataDir,
		notifyURL: notifyURL,
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool {
				return true
			},
		},
	}

	if err := relay.initDatabase(); err != nil {
		return nil, fmt.Errorf("failed to initialize database: %v", err)
	}

	// Start cleanup routine
	go relay.cleanupClients()

	return relay, nil
}

// initDatabase creates the necessary tables
func (r *Relay) initDatabase() error {
	query := `
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
		
		CREATE INDEX IF NOT EXISTS idx_pubkey ON relay_events(pubkey);
		CREATE INDEX IF NOT EXISTS idx_kind ON relay_events(kind);
		CREATE INDEX IF NOT EXISTS idx_created_at ON relay_events(created_at);
		CREATE INDEX IF NOT EXISTS idx_received_at ON relay_events(received_at);
	`
	
	_, err := r.db.Exec(query)
	return err
}

// Close closes the relay
func (r *Relay) Close() error {
	r.clientsMutex.Lock()
	for _, client := range r.clients {
		client.Conn.Close()
	}
	r.clientsMutex.Unlock()
	
	return r.db.Close()
}

// getStats returns relay statistics
func (r *Relay) getStats() map[string]interface{} {
	var eventCount int
	r.db.QueryRow("SELECT COUNT(*) FROM relay_events").Scan(&eventCount)
	
	r.clientsMutex.RLock()
	clientCount := len(r.clients)
	r.clientsMutex.RUnlock()
	
	return map[string]interface{}{
		"events":  eventCount,
		"clients": clientCount,
	}
}

func handleWebSocket(c *gin.Context) {
	conn, err := relay.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}

	client := &Client{
		ID:            generateClientID(),
		Conn:          conn,
		Subscriptions: make(map[string]*Subscription),
		Send:          make(chan []byte, 256),
		Relay:         relay,
		lastSeen:      time.Now(),
	}

	relay.clientsMutex.Lock()
	relay.clients[client.ID] = client
	relay.clientsMutex.Unlock()

	log.Printf("Client %s connected", client.ID)

	go client.writePump()
	go client.readPump()
}

func generateClientID() string {
	return fmt.Sprintf("client_%d_%d", time.Now().UnixNano(), len(relay.clients))
}

// readPump handles reading from the websocket connection
func (c *Client) readPump() {
	defer func() {
		c.Relay.clientsMutex.Lock()
		delete(c.Relay.clients, c.ID)
		c.Relay.clientsMutex.Unlock()
		c.Conn.Close()
		log.Printf("Client %s disconnected", c.ID)
	}()

	c.Conn.SetReadLimit(1024 * 1024) // 1MB
	c.Conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	c.Conn.SetPongHandler(func(string) error {
		c.Conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, message, err := c.Conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("Client %s read error: %v", c.ID, err)
			}
			break
		}

		c.lastSeen = time.Now()
		c.handleMessage(message)
	}
}

// writePump handles writing to the websocket connection
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

			if err := c.Conn.WriteMessage(websocket.TextMessage, message); err != nil {
				log.Printf("Client %s write error: %v", c.ID, err)
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

// handleMessage processes incoming messages
func (c *Client) handleMessage(message []byte) {
	var raw []json.RawMessage
	if err := json.Unmarshal(message, &raw); err != nil {
		log.Printf("Invalid JSON from client %s: %v", c.ID, err)
		return
	}

	if len(raw) == 0 {
		return
	}

	var messageType string
	if err := json.Unmarshal(raw[0], &messageType); err != nil {
		log.Printf("Invalid message type from client %s: %v", c.ID, err)
		return
	}

	switch messageType {
	case "EVENT":
		c.handleEvent(raw)
	case "REQ":
		c.handleSubscription(raw)
	case "CLOSE":
		c.handleClose(raw)
	default:
		log.Printf("Unknown message type from client %s: %s", c.ID, messageType)
	}
}

// handleEvent processes EVENT messages
func (c *Client) handleEvent(raw []json.RawMessage) {
	if len(raw) < 2 {
		return
	}

	var event Event
	if err := json.Unmarshal(raw[1], &event); err != nil {
		log.Printf("Invalid event from client %s: %v", c.ID, err)
		return
	}

	// Validate event
	if !c.validateEvent(&event) {
		c.sendOK(event.ID, false, "ERROR: Invalid event")
		return
	}

	// Handle metadata events
	if event.Kind == 0 {
		c.handleMetadata(&event)
	}

	// Store event
	if err := c.Relay.storeEvent(&event); err != nil {
		c.sendOK(event.ID, false, fmt.Sprintf("ERROR: Failed to store event: %v", err))
		return
	}

	c.sendOK(event.ID, true, "")

	// Broadcast to subscribers
	c.Relay.broadcastEvent(&event)
}

// validateEvent validates an event
func (c *Client) validateEvent(event *Event) bool {
	// Check required fields
	if event.ID == "" || event.PubKey == "" || event.Sig == "" {
		return false
	}

	// Verify event ID
	expectedID := c.calculateEventID(event)
	if event.ID != expectedID {
		log.Printf("Event ID mismatch: expected %s, got %s", expectedID, event.ID)
		return false
	}

	return true
}

// calculateEventID calculates the event ID
func (c *Client) calculateEventID(event *Event) string {
	tagsJSON, _ := json.Marshal(event.Tags)
	
	serialized := fmt.Sprintf(`[0,"%s",%d,%d,%s,"%s"]`,
		event.PubKey,
		event.CreatedAt,
		event.Kind,
		string(tagsJSON),
		event.Content,
	)
	
	hash := sha256.Sum256([]byte(serialized))
	return hex.EncodeToString(hash[:])
}

// handleMetadata processes metadata events (kind 0)
func (c *Client) handleMetadata(event *Event) {
	log.Printf("📝 Metadata event from %s", event.PubKey[:8])
}

// sendOK sends an OK message to the client
func (c *Client) sendOK(eventID string, success bool, message string) {
	response := []interface{}{"OK", eventID, success, message}
	data, _ := json.Marshal(response)
	
	select {
	case c.Send <- data:
	default:
		close(c.Send)
	}
}

// handleSubscription processes REQ messages
func (c *Client) handleSubscription(raw []json.RawMessage) {
	if len(raw) < 3 {
		return
	}

	var subID string
	if err := json.Unmarshal(raw[1], &subID); err != nil {
		return
	}

	var filters []Filter
	for i := 2; i < len(raw); i++ {
		var filter Filter
		if err := json.Unmarshal(raw[i], &filter); err != nil {
			continue
		}
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

	// Send matching events
	events := c.Relay.getMatchingEvents(filters)
	for _, event := range events {
		eventData := []interface{}{"EVENT", subID, event}
		data, _ := json.Marshal(eventData)
		
		select {
		case c.Send <- data:
		default:
			close(c.Send)
			return
		}
	}

	// Send EOSE
	eoseData := []interface{}{"EOSE", subID}
	data, _ := json.Marshal(eoseData)
	select {
	case c.Send <- data:
	default:
		close(c.Send)
	}

	log.Printf("Sent %d events for subscription %s", len(events), subID)
}

// handleClose processes CLOSE messages
func (c *Client) handleClose(raw []json.RawMessage) {
	if len(raw) < 2 {
		return
	}

	var subID string
	if err := json.Unmarshal(raw[1], &subID); err != nil {
		return
	}

	c.mu.Lock()
	delete(c.Subscriptions, subID)
	c.mu.Unlock()

	log.Printf("Closed subscription %s for client %s", subID, c.ID)
}

// getMatchingEvents retrieves events matching the filters
func (r *Relay) getMatchingEvents(filters []Filter) []Event {
	var events []Event
	
	for _, filter := range filters {
		query := "SELECT id, pubkey, created_at, kind, tags, content, sig FROM relay_events WHERE 1=1"
		var args []interface{}
		
		if len(filter.Authors) > 0 {
			placeholders := make([]string, len(filter.Authors))
			for i, author := range filter.Authors {
				placeholders[i] = "?"
				args = append(args, author)
			}
			query += " AND pubkey IN (" + strings.Join(placeholders, ",") + ")"
		}
		
		if len(filter.Kinds) > 0 {
			placeholders := make([]string, len(filter.Kinds))
			for i, kind := range filter.Kinds {
				placeholders[i] = "?"
				args = append(args, kind)
			}
			query += " AND kind IN (" + strings.Join(placeholders, ",") + ")"
		}
		
		if filter.Since != nil {
			query += " AND created_at >= ?"
			args = append(args, *filter.Since)
		}
		
		if filter.Until != nil {
			query += " AND created_at <= ?"
			args = append(args, *filter.Until)
		}
		
		query += " ORDER BY created_at DESC"
		
		if filter.Limit != nil {
			query += " LIMIT ?"
			args = append(args, *filter.Limit)
		}
		
		rows, err := r.db.Query(query, args...)
		if err != nil {
			log.Printf("Query error: %v", err)
			continue
		}
		
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
				log.Printf("Scan error: %v", err)
				continue
			}
			
			json.Unmarshal([]byte(tagsJSON), &event.Tags)
			events = append(events, event)
		}
		
		rows.Close()
	}
	
	return events
}

// broadcastEvent broadcasts an event to all matching subscriptions
func (r *Relay) broadcastEvent(event *Event) {
	r.clientsMutex.RLock()
	defer r.clientsMutex.RUnlock()
	
	for _, client := range r.clients {
		client.mu.RLock()
		for subID, sub := range client.Subscriptions {
			if r.eventMatchesFilters(event, sub.Filters) {
				eventData := []interface{}{"EVENT", subID, event}
				data, _ := json.Marshal(eventData)
				
				select {
				case client.Send <- data:
				default:
					close(client.Send)
				}
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

// eventMatchesFilter checks if an event matches a filter
func (r *Relay) eventMatchesFilter(event *Event, filter Filter) bool {
	if len(filter.Authors) > 0 {
		found := false
		for _, author := range filter.Authors {
			if event.PubKey == author {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	
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
	
	if filter.Since != nil && event.CreatedAt < *filter.Since {
		return false
	}
	
	if filter.Until != nil && event.CreatedAt > *filter.Until {
		return false
	}
	
	return true
}

func formatTags(tags [][]string) string {
	result, _ := json.Marshal(tags)
	return string(result)
}

// storeEvent stores an event in the database and notifies the Python app
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
	
	if err != nil {
		return err
	}
	
	log.Printf("📝 Stored event %s (kind %d) from %s", event.ID[:8], event.Kind, event.PubKey[:8])
	
	// Trigger notification to Python app (throttled to avoid spam)
	go r.notifyPythonApp()
	
	return nil
}

// notifyPythonApp sends a notification to the Python application
func (r *Relay) notifyPythonApp() {
	r.notifyMutex.Lock()
	defer r.notifyMutex.Unlock()
	
	// Throttle notifications - only send one every 30 seconds
	if time.Since(r.lastNotify) < 30*time.Second {
		return
	}
	
	r.lastNotify = time.Now()
	
	log.Printf("🔔 Notifying Python app for cache update...")
	
	client := &http.Client{
		Timeout: 10 * time.Second,
	}
	
	resp, err := client.Post(r.notifyURL, "application/json", bytes.NewBuffer([]byte("{}")))
	if err != nil {
		log.Printf("❌ Failed to notify Python app: %v", err)
		return
	}
	defer resp.Body.Close()
	
	if resp.StatusCode == 200 {
		log.Printf("✅ Python app notified successfully")
	} else {
		log.Printf("⚠️  Python app notification returned status: %d", resp.StatusCode)
	}
}

// cleanupClients removes inactive clients
func (r *Relay) cleanupClients() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	
	for range ticker.C {
		r.clientsMutex.Lock()
		for id, client := range r.clients {
			if time.Since(client.lastSeen) > 2*time.Minute {
				client.Conn.Close()
				delete(r.clients, id)
				log.Printf("Cleaned up inactive client %s", id)
			}
		}
		r.clientsMutex.Unlock()
	}
}
