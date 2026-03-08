# imse-social-reading-hub

A web application for social reading of books from [Project Gutenberg](https://www.gutenberg.org/). Users can read books, leave comments, and interact with other readers.

## Features
- Fontawesome and Bootstrap integration for UI
- Custom DB access wrapper for database interactions, check [DBProvider interface](./db/DBProvider.py) for descriptions of each method.
- Self-signed certificate
- Random data generation
- MongoDB and MySQL support
- Data migration from MySQL to MongoDB

## Setup instructions
Everything required for running the application is provided, including a default `.env` file. This file contains no sensitive information, and is only used for development purposes. It is highly important to change the values in the `.env` when deploying to a publicly accessible environment.

To run the application, use `docker compose up --build` or run the provided `build.sh` script.

After the setup has been successfully built and deployed, it can be accessed on `https://localhost:8000`