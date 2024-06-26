class CryptoTransactionsCard extends HTMLElement {
    set hass(hass) {
        if (!this.content) {
            const card = document.createElement('ha-card');
            card.header = 'Transactions';
            this.content = document.createElement('div');
            card.appendChild(this.content);
            this.appendChild(card);
        }

        const entryId = this.config.entry_id;
        const cryptoId = this.config.crypto_id;

        hass.callApi('GET', `portfolio_crypto/transactions/${entryId}/${cryptoId}`).then(transactions => {
            this.content.innerHTML = `
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
            `;

            this.querySelectorAll('.delete').forEach(button => {
                button.addEventListener('click', e => {
                    const transactionId = e.target.dataset.id;
                    hass.callService('portfolio_crypto', 'delete_transaction', { entry_id: entryId, transaction_id: transactionId });
                });
            });

            this.querySelectorAll('.edit').forEach(button => {
                button.addEventListener('click', e => {
                    const transactionId = e.target.dataset.id;
                    // Ouvrir un modal pour éditer la transaction
                });
            });

            this.querySelector('#add').addEventListener('click', () => {
                // Ouvrir un modal pour ajouter une nouvelle transaction
            });
        });
    }

    setConfig(config) {
        if (!config.entry_id || !config.crypto_id) {
            throw new Error('Vous devez définir un entry_id et un crypto_id');
        }
        this.config = config;
    }

    getCardSize() {
        return 1;
    }
}

customElements.define('crypto-transactions-card', CryptoTransactionsCard);
