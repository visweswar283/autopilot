package service

import (
	"crypto/tls"
	"fmt"
	"log"
	"net"
	"net/smtp"
	"strings"
)

// EmailService sends transactional emails.
// Configure via SMTP_HOST/PORT/USER/PASS/FROM env vars.
// If SMTP_HOST is empty the service silently skips sending (dev mode).
type EmailService struct {
	host    string
	port    string
	user    string
	pass    string
	from    string
	appURL  string
	enabled bool
}

func NewEmailService(host, port, user, pass, from, appURL string) *EmailService {
	enabled := host != "" && user != "" && pass != ""
	if !enabled {
		log.Println("[email] SMTP not configured — password reset emails will be skipped")
	}
	return &EmailService{
		host:    host,
		port:    port,
		user:    user,
		pass:    pass,
		from:    from,
		appURL:  strings.TrimRight(appURL, "/"),
		enabled: enabled,
	}
}

// SendPasswordReset sends a password-reset email with the given token.
func (e *EmailService) SendPasswordReset(toEmail, token string) error {
	if !e.enabled {
		// Log the reset URL so it can be used during development/testing
		log.Printf("[email] SMTP disabled — reset URL: %s/reset-password?token=%s", e.appURL, token)
		return nil
	}

	resetURL := fmt.Sprintf("%s/reset-password?token=%s", e.appURL, token)

	subject := "Reset your ApplyPilot password"
	htmlBody := fmt.Sprintf(`<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#0f1117;color:#e2e8f0;padding:40px 20px">
  <div style="max-width:520px;margin:0 auto;background:#1a1f2e;border-radius:12px;padding:40px;border:1px solid rgba(255,255,255,0.1)">
    <div style="text-align:center;margin-bottom:32px">
      <span style="font-size:24px;font-weight:bold;color:#fff">⚡ ApplyPilot</span>
    </div>
    <h2 style="color:#fff;margin-bottom:12px">Reset your password</h2>
    <p style="color:#94a3b8;line-height:1.6">
      We received a request to reset the password for your ApplyPilot account.<br>
      Click the button below to choose a new password — this link expires in <strong style="color:#fff">1 hour</strong>.
    </p>
    <div style="text-align:center;margin:32px 0">
      <a href="%s" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:600;font-size:16px;display:inline-block">
        Reset Password
      </a>
    </div>
    <p style="color:#64748b;font-size:13px">
      Or copy and paste this link into your browser:<br>
      <a href="%s" style="color:#818cf8;word-break:break-all">%s</a>
    </p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:24px 0">
    <p style="color:#64748b;font-size:12px;margin:0">
      If you didn't request a password reset, you can safely ignore this email.
      Your password will not be changed.
    </p>
  </div>
</body>
</html>`, resetURL, resetURL, resetURL)

	msg := buildMIMEMessage(e.from, toEmail, subject, htmlBody)
	return e.sendSMTP(toEmail, []byte(msg))
}

// SendWelcome sends a welcome email after registration.
func (e *EmailService) SendWelcome(toEmail, fullName string) error {
	if !e.enabled {
		return nil
	}

	name := fullName
	if name == "" {
		parts := strings.Split(toEmail, "@")
		name = parts[0]
	}

	subject := "Welcome to ApplyPilot — let's start applying"
	htmlBody := fmt.Sprintf(`<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#0f1117;color:#e2e8f0;padding:40px 20px">
  <div style="max-width:520px;margin:0 auto;background:#1a1f2e;border-radius:12px;padding:40px;border:1px solid rgba(255,255,255,0.1)">
    <div style="text-align:center;margin-bottom:32px">
      <span style="font-size:24px;font-weight:bold;color:#fff">⚡ ApplyPilot</span>
    </div>
    <h2 style="color:#fff;margin-bottom:12px">Welcome, %s!</h2>
    <p style="color:#94a3b8;line-height:1.6">
      Your account is ready. Here's how to get started:
    </p>
    <ol style="color:#94a3b8;line-height:2">
      <li>Complete your <strong style="color:#fff">profile</strong> — name, skills, target roles</li>
      <li>Upload your <strong style="color:#fff">resume</strong></li>
      <li>Configure <strong style="color:#fff">auto-apply settings</strong></li>
      <li>Watch ApplyPilot apply to jobs on your behalf</li>
    </ol>
    <div style="text-align:center;margin:32px 0">
      <a href="%s/dashboard" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:600;font-size:16px;display:inline-block">
        Go to Dashboard
      </a>
    </div>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:24px 0">
    <p style="color:#64748b;font-size:12px;margin:0">
      ApplyPilot — Automate your job search
    </p>
  </div>
</body>
</html>`, name, e.appURL)

	msg := buildMIMEMessage(e.from, toEmail, subject, htmlBody)
	return e.sendSMTP(toEmail, []byte(msg))
}

func buildMIMEMessage(from, to, subject, htmlBody string) string {
	return fmt.Sprintf(
		"From: ApplyPilot <%s>\r\nTo: %s\r\nSubject: %s\r\n"+
			"MIME-Version: 1.0\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n%s",
		from, to, subject, htmlBody,
	)
}

func (e *EmailService) sendSMTP(toEmail string, msg []byte) error {
	addr := net.JoinHostPort(e.host, e.port)
	auth := smtp.PlainAuth("", e.user, e.pass, e.host)

	// Use STARTTLS on port 587 (standard for SES/SendGrid SMTP)
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		return fmt.Errorf("smtp dial: %w", err)
	}

	client, err := smtp.NewClient(conn, e.host)
	if err != nil {
		return fmt.Errorf("smtp client: %w", err)
	}
	defer client.Close()

	tlsConfig := &tls.Config{ServerName: e.host}
	if err = client.StartTLS(tlsConfig); err != nil {
		return fmt.Errorf("smtp starttls: %w", err)
	}

	if err = client.Auth(auth); err != nil {
		return fmt.Errorf("smtp auth: %w", err)
	}

	if err = client.Mail(e.from); err != nil {
		return fmt.Errorf("smtp mail from: %w", err)
	}

	if err = client.Rcpt(toEmail); err != nil {
		return fmt.Errorf("smtp rcpt: %w", err)
	}

	w, err := client.Data()
	if err != nil {
		return fmt.Errorf("smtp data: %w", err)
	}
	defer w.Close()

	if _, err = w.Write(msg); err != nil {
		return fmt.Errorf("smtp write: %w", err)
	}

	return nil
}
