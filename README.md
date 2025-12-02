# Surfing Project 🏄‍♂️

**Surfing Project** is a web platform designed to help surfers organize their life on the water. Unlike typical social media, this tool focuses on utility: finding spots, planning sessions, and coordinating with friends.

> **Current Status:** 🚧 Under Development (MVP Phase)

## 🎯 Project Goal
To create a "tool for handling surf life" rather than just another social feed. The core value lies in coordination—knowing **where**, **when**, and **with whom** to surf.

## 🌟 Key Features

### 1. Accounts & Profiles
* Custom User Model (Email-based login).
* User Profiles with bio, country, and avatar.
* Secure authentication system.

### 2. Surf Spots
* Database of surfing spots with coordinates and descriptions.
* Community-driven: Users can add and discover new spots.
* Filtering by location and difficulty (planned).

### 3. Surf Sessions (The Heart of the App) 
* Organize sessions (e.g., "Dawn patrol at Hel, 6:00 AM").
* Join/Leave functionality for participants.
* Session status tracking (Planned / Completed / Canceled).
* Session-specific comments for coordination.

### 4. Future Roadmap 🚀
* **Social Connections:** Friends lists and "follow" logic.
* **Session Logs (Mini-Strava):** Post-session reports with photos and ratings.
* **Notifications & Messages:** Internal messaging system and alerts for upcoming sessions.

## 🛠️ Tech Stack

* **Backend:** Python 3.12, Django 5.x
* **Database:** PostgreSQL
* **Containerization:** Docker & Docker Compose
* **Frontend:** HTML5, CSS3, Bootstrap 5 (Focus on clean, responsive UI)
* **Testing:** Pytest, Pytest-Django

## 📂 Project Structure

The project is organized into modular apps for scalability:

```text
.
├── accounts/          # Auth & Profiles
├── core/              # Main settings & Home
├── spots/             # Spot management
├── media/             # User uploads (avatars)
├── static/            # CSS, JS, Images
├── templates/         # HTML Templates (base, home, accounts)
├── Dockerfile
├── docker-compose.yml
├── manage.py
└── requirements.txt