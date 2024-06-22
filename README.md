# Portfolio Crypto

An addon to manage and monitor your crypto investments.

## Installation

1. Go to Supervisor -> Add-on Store.
2. Click on the three dots in the upper right corner and select "Repositories".
3. Add the following URL: `https://github.com/<your-username>/homeassistant-portfolio-crypto`.
4. Find "Portfolio Crypto" in the list of add-ons and install it.

## Configuration

No configuration options are required.

## Usage

- The addon provides an API to add, modify, and delete crypto transactions.
- Access the API at `http://<your-home-assistant-ip>:5000`.

## API Endpoints

- `GET /transactions` - List all transactions
- `POST /transaction` - Add a new transaction
- `PUT /transaction/<id>` - Update a transaction
- `DELETE /transaction/<id>` - Delete a transaction

For more details, refer to the [documentation](https://github.com/<your-username>/homeassistant-portfolio-crypto).
