# Food Wastage Prediction and Redistribution System

## Overview
A web-based system for predicting food requirements for events and facilitating the redistribution of excess food to needy organizations.

## Features
- User authentication
- Food wastage prediction
- Organization matching
- Donation management
- Profile management

## Setup Instructions
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up MongoDB:
   - Install MongoDB Compass
   - Create database: `food_wastage_db`
   - Create collections: `users`, `predictions`, `organizations`, `donations`
4. Configure environment variables:
   - Create `.env` file
   - Add MongoDB URI and secret key
5. Run the application:
   ```bash
   python app.py
   ```

## Technologies Used
- Python
- Flask
- MongoDB
- Machine Learning
- HTML/CSS/JavaScript

## Project Structure
```
Food_Wastage_Prediction_And_Redistribution/
├── app.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── predict.html
│   └── profile.html
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── models/
│   └── prediction_model.py
└── project_details/
    └── documentation/
```

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
MIT License 
