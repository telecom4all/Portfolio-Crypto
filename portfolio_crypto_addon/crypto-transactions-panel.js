class CryptoTransactionsPanel extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    set hass(hass) {
        if (!this.panel.config) {
            console.error('Configuration non définie');
            return;
        }

        const entryId = this.panel.config.entry_id;
        const cryptoId = this.panel.config.crypto_id;

        this.fetchAndRenderTransactions(entryId, cryptoId);
    }

    async fetchAndRenderTransactions(entryId, cryptoId) {
        try {
            const transactions = await this.fetchTransactions(entryId);

            // Filtrer les transactions pour le crypto_id donné
            const filteredTransactions = transactions.filter(transaction => transaction.crypto_id === cryptoId);
            this.render(filteredTransactions);
        } catch (error) {
            console.error('Erreur lors de la récupération des transactions:', error);
        }
    }

    async fetchTransactions(entryId) {
        const baseUrl = `${window.location.protocol}//${window.location.hostname}`;
        const url = `${baseUrl}:5000/transactions/${entryId}`;
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            return await response.json();
        } else {
            const errorText = await response.text();
            throw new Error(`Erreur ${response.status}: ${errorText}`);
        }
    }

    render(transactions) {
        if (!transactions || transactions.length === 0) {
            this.shadowRoot.innerHTML = '<div>Aucune transaction trouvée.</div>';
            return;
        }

        this.shadowRoot.innerHTML = `
            <style>
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                th {
                    background-color: #f2f2f2;
                }
                tr:hover {
                    background-color: #f5f5f5;
                }
                button {
                    margin: 4px;
                    padding: 8px 12px;
                    border: none;
                    cursor: pointer;
                }
            </style>
            <div>
                <h1>Transactions pour ${this.panel.config.crypto_name}</h1>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Nom</th>
                        <th>Quantité</th>
                        <th>Prix</th>
                        <th>Type</th>
                        <th>Date</th>
                        <th>Actions</th>
                    </tr>
                    ${transactions.map(transaction => `
                        <tr>
                            <td>${transaction.id}</td>
                            <td>${transaction.crypto_name}</td>
                            <td>${transaction.quantity}</td>
                            <td>${transaction.price_usd}</td>
                            <td>${transaction.transaction_type}</td>
                            <td>${transaction.date}</td>
                            <td>
                                <button class="edit" data-id="${transaction.id}">Modifier</button>
                                <button class="delete" data-id="${transaction.id}">Supprimer</button>
                            </td>
                        </tr>
                    `).join('')}
                </table>
                <button id="add">Ajouter une transaction</button>
            </div>
        `;

        this.shadowRoot.querySelectorAll('.delete').forEach(button => {
            button.addEventListener('click', e => {
                const transactionId = e.target.dataset.id;
                this.hass.callService('portfolio_crypto', 'delete_transaction', { entry_id: this.panel.config.entry_id, transaction_id: transactionId });
            });
        });

        this.shadowRoot.querySelectorAll('.edit').forEach(button => {
            button.addEventListener('click', e => {
                const transactionId = e.target.dataset.id;
                // Open a modal to edit the transaction
            });
        });

        this.shadowRoot.querySelector('#add').addEventListener('click', () => {
            // Open a modal to add a new transaction
        });
    }

    setConfig(config) {
        if (!config.entry_id || !config.crypto_id || !config.crypto_name) {
            throw new Error('Vous devez définir un entry_id, un crypto_id, et un crypto_name');
        }
        this.panel.config = config;
    }

    getCardSize() {
        return 1;
    }
}

customElements.define('crypto-transactions-panel', CryptoTransactionsPanel);
