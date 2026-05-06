# Surfing Project

Surfing Project is a Django web application built around one core idea: make organizing surf sessions easier than using generic social media or scattered group chats.

The app combines surf spot discovery, session planning, lightweight social features, messaging, and notifications in one product-oriented MVP. It is designed as a portfolio project, but implemented with realistic app structure, Dockerized startup, media uploads, tests, and deployment-minded defaults.

Surfing Project is a redesigned and improved successor to my earlier project, [SurferGuide](https://github.com/eliaszpiotr?utm_source=chatgpt.com), rebuilt with a cleaner architecture, better scalability, and a stronger focus on real-world surf session coordination.

## What The Project Does

The app allows users to:

- create an account and manage a personal profile
- add and browse surf spots with coordinates, surf details, and descriptions
- create surf sessions for a specific spot
- join and leave sessions
- upload community photos to spots with captions
- follow other users
- open private 1:1 conversations with other surfers
- use a session chat visible to the organizer and participants
- receive notifications for follows and new messages

This is not meant to be a generic “social feed.” The main product focus is coordination:

- where to surf
- when to surf
- with whom to surf

## Main Features

### Accounts and Profiles

- custom user model with email-based authentication
- public user profiles by username
- avatar, country, and bio editing
- followers / following system
- uploaded spot photos shown on the user profile

### Surf Spots

- create, edit, and delete spots
- store coordinates, country, location details, break type, difficulty, swell and wind direction
- detail page with map and sessions
- community photo gallery with captions

### Surf Sessions

- create sessions with date, time, note, and optional participant limit
- join and leave session flow
- organizer-only edit and delete actions
- upcoming and history session splits on profile pages

### Messaging

- private direct conversations between users
- public chat inside a session
- access control for session chat based on participation

### Notifications

- follow notifications
- direct message notifications
- session message notifications
- unread counter in the navigation

## Tech Stack

- Python 3.12
- Django 5
- PostgreSQL
- Docker and Docker Compose
- Bootstrap 5
- Pillow
- Pytest + pytest-django
- WhiteNoise
- Gunicorn

## Project Structure

```text
.
├── accounts/          # Authentication, profiles, following
├── chat/              # Direct chat and session chat
├── core/              # Home page, settings helpers, demo seed command
├── notifications/     # Notification inbox and unread counts
├── spots/             # Surf spots and community photos
├── surf_sessions/     # Session planning and participation
├── static/            # CSS and JavaScript
├── templates/         # HTML templates
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── manage.py
└── requirements.txt
```

## Run With Docker

Docker is the primary way to run this project.

### Start

From the project root:

```bash
docker compose down -v
docker compose up --build
```

This will:

- start PostgreSQL
- build the Django image
- apply migrations
- collect static files
- seed demo data automatically
- run the app with Gunicorn

### Open The App

Open: [http://localhost:8000](http://localhost:8000)

### Demo Accounts

The Docker setup seeds demo accounts automatically:

- `demo.anna@example.com` / `pass1234`
- `demo.marc@example.com` / `pass1234`
- `demo.kai@example.com` / `pass1234`

## Environment Notes

The current container setup is designed for local/demo usage:

- app bound to `127.0.0.1:8000`
- PostgreSQL not exposed publicly
- `DEBUG=False`
- local media served explicitly for demo purposes

## Demo Data

The demo seed creates:

- demo users
- demo spots
- demo sessions
- demo spot gallery images
- demo profile images

The seed command is written to be idempotent, so repeated runs should not create duplicate demo records.

## Why This Project Exists

This project was built to show practical full-stack product thinking, not just isolated CRUD screens.

The focus areas include:

- clean Django app separation
- realistic user flows
- controlled permissions
- Dockerized setup for fast review
- media handling
- messaging and notifications
- regression tests for core behavior

## Current Scope

This is still an MVP, not a finished production.

Areas intentionally kept simple:

- no WebSockets yet, chat is request/response based
- no advanced search or recommendation engine
- notifications are inbox-style, not realtime push
- no cloud object storage for uploads yet
- no production reverse proxy setup included in repo

## License

This project is source-available for portfolio and viewing purposes only.
All rights reserved.
Unauthorized use, copying, modification, or distribution is prohibited.
