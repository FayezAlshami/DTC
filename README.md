# DTC Job Bot - Student Service Marketplace

A comprehensive Telegram bot that connects students who want to provide services with users who want to request services. Built with Python, PostgreSQL, and Aiogram 3.x.

## Features

- **User Authentication**: Registration with email verification and secure login
- **Role-Based Access**: Admin, Student, and Regular User roles
- **Profile Management**: Complete profile with student-specific fields
- **Service Provision**: Students can post services with media, pricing, and descriptions
- **Service Requests**: Users can request services with budget and specialization filters
- **Browse & Filter**: Search services by specialization and price range
- **Contact Management**: Secure contact request/response system
- **Records Tracking**: View all your services, requests, and interactions
- **Admin Panel**: Moderation, user management, statistics, and more

## Tech Stack

- **Python 3.10+**
- **Aiogram 3.13.1** - Modern async Telegram Bot framework
- **PostgreSQL** - Database
- **SQLAlchemy 2.0** - ORM with async support
- **AsyncPG** - Async PostgreSQL driver
- **Alembic** - Database migrations (optional)

## Prerequisites

1. Python 3.10 or higher
2. PostgreSQL 12 or higher
3. Telegram Bot Token (from [@BotFather](https://t.me/botfather))
4. SMTP email credentials (for verification codes)
5. Two Telegram channels (for services and requests)

## Installation

1. **Clone the repository** (or navigate to the project directory)

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up PostgreSQL database**:
   ```sql
   CREATE DATABASE dtc_job_bot;
   CREATE USER dtc_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE dtc_job_bot TO dtc_user;
   ```

6. **Configure environment variables**:
   - Copy `.env.example` to `.env`
   - Fill in all required values:
     ```env
     BOT_TOKEN=your_bot_token_from_botfather
     DB_HOST=localhost
     DB_PORT=5432
     DB_NAME=dtc_job_bot
     DB_USER=dtc_user
     DB_PASSWORD=your_password
     SMTP_HOST=smtp.gmail.com
     SMTP_PORT=587
     SMTP_USER=your_email@gmail.com
     SMTP_PASSWORD=your_app_password
     EMAIL_FROM=your_email@gmail.com
     SERVICES_CHANNEL_ID=@your_services_channel
     REQUESTS_CHANNEL_ID=@your_requests_channel
     ADMIN_USER_IDS=123456789,987654321
     VERIFICATION_CODE_EXPIRY_MINUTES=10
     ```

7. **Set up Telegram channels**:
   - Create two channels: one for services, one for requests
   - Add your bot as an administrator to both channels
   - Get the channel usernames (e.g., `@your_services_channel`) or IDs
   - Update `SERVICES_CHANNEL_ID` and `REQUESTS_CHANNEL_ID` in `.env`

8. **Run the bot**:
   ```bash
   python main.py
   ```

## Project Structure

```
.
├── main.py                 # Bot entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── database/
│   ├── __init__.py
│   ├── base.py            # Database connection and base
│   └── models.py          # SQLAlchemy models
├── repositories/
│   ├── __init__.py
│   ├── user_repository.py
│   ├── verification_repository.py
│   ├── service_repository.py
│   ├── request_repository.py
│   ├── contact_repository.py
│   └── admin_repository.py
├── services/
│   ├── __init__.py
│   ├── email_service.py
│   ├── auth_service.py
│   ├── profile_service.py
│   ├── service_service.py
│   └── request_service.py
└── handlers/
    ├── __init__.py
    ├── common.py          # Middleware and utilities
    ├── keyboards.py       # Keyboard builders
    ├── start_handler.py   # Start and authentication
    ├── profile_handler.py # Profile management
    ├── service_handler.py # Provide service flow
    ├── request_handler.py # Request service flow
    ├── browse_handler.py  # Browse services
    ├── records_handler.py # User records
    └── admin_handler.py   # Admin panel
```

## Usage

### For Users

1. Start the bot with `/start`
2. Create an account or log in
3. Complete your profile (required for students who want to provide services)
4. Use the main menu to:
   - **Provide a Service**: Post services you can offer (students only)
   - **Request a Service**: Post what you need
   - **Browse Filtered Services**: Search for services
   - **Your Records**: View your history

### For Admins

1. Access admin panel with `/admin`
2. Available features:
   - Service Moderation
   - Request Moderation
   - User Management
   - Statistics
   - View Logs

## Database Schema

The bot uses the following main tables:
- `users` - User accounts and profiles
- `verification_codes` - Email verification codes
- `services` - Services provided by students
- `service_requests` - Service requests from users
- `contact_requests` - Contact request interactions
- `admin_logs` - Admin action logs

## Security Features

- Passwords are hashed using bcrypt
- Email verification required for registration
- Verification codes expire after configured time
- Role-based access control
- Input validation on all user inputs

## Configuration

Key configuration options in `config.py`:
- `MAX_DESCRIPTION_LENGTH`: Maximum description length (default: 3000)
- `MAX_TITLE_LENGTH`: Maximum title length (default: 200)
- `VERIFICATION_CODE_EXPIRY_MINUTES`: Code expiration time (default: 10)

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Verify database exists and user has permissions

### Email Not Sending
- For Gmail, use an App Password (not your regular password)
- Check SMTP settings in `.env`
- Verify firewall allows SMTP connections

### Bot Not Responding
- Check bot token is correct
- Ensure bot is added as admin to channels
- Check channel IDs/usernames are correct
- Review logs for errors

## Development

### Adding New Features

The project follows a clean architecture:
1. **Models** (`database/models.py`): Define data structures
2. **Repositories** (`repositories/`): Database access layer
3. **Services** (`services/`): Business logic
4. **Handlers** (`handlers/`): Bot interaction layer

### Running Tests

(Add test instructions when tests are implemented)

## License

[Specify your license]

## Support

For issues and questions, please [create an issue](link-to-issues) or contact the development team.

