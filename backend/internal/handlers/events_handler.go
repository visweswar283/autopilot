package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
)

const applyEventsChannel = "apply:events"

// EventsHandler streams real-time application events to the browser via SSE.
type EventsHandler struct {
	rdb *redis.Client
}

func NewEventsHandler(rdb *redis.Client) *EventsHandler {
	return &EventsHandler{rdb: rdb}
}

// Stream subscribes to the Redis apply:events channel and forwards events
// matching the authenticated user to the browser as Server-Sent Events.
//
// GET /api/v1/events/stream
func (h *EventsHandler) Stream(c *gin.Context) {
	userID := c.GetString("user_id")

	c.Header("Content-Type",  "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection",    "keep-alive")
	c.Header("X-Accel-Buffering", "no") // disable nginx buffering

	ctx, cancel := context.WithCancel(c.Request.Context())
	defer cancel()

	pubsub := h.rdb.Subscribe(ctx, applyEventsChannel)
	defer pubsub.Close()

	// Send a connected heartbeat immediately
	h.writeEvent(c, "connected", gin.H{"status": "ok", "user_id": userID})

	// Heartbeat ticker to keep the connection alive through proxies
	ticker := time.NewTicker(25 * time.Second)
	defer ticker.Stop()

	msgCh := pubsub.Channel()

	for {
		select {
		case <-c.Request.Context().Done():
			return

		case <-ticker.C:
			h.writeComment(c, "heartbeat")

		case msg, ok := <-msgCh:
			if !ok {
				return
			}
			// Parse event and filter to the authenticated user
			var event map[string]any
			if err := json.Unmarshal([]byte(msg.Payload), &event); err != nil {
				continue
			}
			if event["user_id"] != userID {
				continue
			}
			h.writeEvent(c, fmt.Sprintf("%v", event["type"]), event)
		}
	}
}

func (h *EventsHandler) writeEvent(c *gin.Context, eventType string, data any) {
	payload, _ := json.Marshal(data)
	fmt.Fprintf(c.Writer, "event: %s\ndata: %s\n\n", eventType, payload)
	c.Writer.Flush()
}

func (h *EventsHandler) writeComment(c *gin.Context, comment string) {
	fmt.Fprintf(c.Writer, ": %s\n\n", comment)
	c.Writer.Flush()
}
