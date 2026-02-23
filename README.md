# Expense Tracker with Templates

A Django-based expense tracking application with JWT authentication and email verification.

## Features

- User authentication with JWT tokens
- Email-based account verification
- Expense tracking and management
- User account management
- Secure password handling

## Project Structure

```
proj_expense_tracker/
├── accounts/              # User authentication and account management
│   ├── models.py         # User models
│   ├── views.py          # Authentication views
│   ├── urls.py           # Account URL routes
│   ├── authentication.py  # JWT authentication logic
│   └── migrations/       # Database migrations
│
├── expenses/             # Expense tracking functionality
│   ├── models.py         # Expense models
│   ├── views.py          # Expense views
│   ├── urls.py           # Expense URL routes
│   └── migrations/       # Database migrations
│
├── proj_expense_tracker/ # Project configuration
│   ├── settings.py       # Django settings
│   ├── urls.py           # Main URL configuration
│   ├── wsgi.py           # WSGI configuration
│   └── asgi.py           # ASGI configuration
│
├── static/               # Static files (CSS, JS, images)
├── templates/            # HTML templates
├── manage.py             # Django management script
└── README.md             # This file
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/codebyrishi3075/Expense_Tracker_with_Templates.git
cd proj_expense_tracker
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with the following variables:
```
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
JWT_REFRESH_SECRET_KEY=your_jwt_refresh_secret_key
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEBUG=True
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000/`

## API Endpoints

### Authentication
- `POST /accounts/register/` - Register a new user
- `POST /accounts/login/` - Login user
- `POST /accounts/refresh/` - Refresh JWT token
- `POST /accounts/verify-email/` - Verify email

### Expenses
- `GET /expenses/` - List all expenses
- `POST /expenses/` - Create a new expense
- `GET /expenses/<id>/` - Retrieve expense details
- `PUT /expenses/<id>/` - Update an expense
- `DELETE /expenses/<id>/` - Delete an expense

## Technologies Used

- **Django** - Web framework
- **Django REST Framework** - REST API development
- **JWT** - JSON Web Tokens for authentication
- **Python** - Programming language

## Environment Variables

Create a `.env` file in the project root with:

- `SECRET_KEY` - Django secret key
- `JWT_SECRET_KEY` - JWT access token secret
- `JWT_REFRESH_SECRET_KEY` - JWT refresh token secret
- `EMAIL_HOST_USER` - Gmail address for email verification
- `EMAIL_HOST_PASSWORD` - Gmail app password
- `DEBUG` - Debug mode (True/False)

## License

This project is licensed under the MIT License.

## Author

Rishikesh - [GitHub](https://github.com/codebyrishi3075)

## Support

For issues and questions, please create an issue on the GitHub repository.
