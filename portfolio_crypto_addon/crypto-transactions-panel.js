class CryptoTransactionsPanel extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    set hass(hass) {
        this._hass = hass;
        if (!this.panel.config) {
            console.error('Configuration non définie');
            return;
        }

        const entryId = this.panel.config.entry_id;
        this.render(); // Render the basic layout including the select element
        this.loadCryptos(entryId);
    }

    async loadCryptos(entryId) {
        try {
            const cryptos = await this.fetchCryptos(entryId);
            if (cryptos.length > 0) {
                this.renderCryptoSelect(cryptos);
                const selectElement = this.shadowRoot.querySelector('#cryptoSelect');
                if (selectElement) {
                    const selectedCryptoId = selectElement.value;
                    const selectedCryptoName = selectElement.options[selectElement.selectedIndex].text.split(' - ')[0];
                    this.updateFormFields(selectedCryptoId, selectedCryptoName);
                    this.fetchAndRenderTransactions(entryId, selectedCryptoId);
                }
            }
        } catch (error) {
            console.error('Erreur lors de la récupération des cryptos:', error);
        }
    }

    async fetchCryptos(entryId) {
        const url = `/api/hassio/ingress/portfolio_crypto/fetch_cryptos/${entryId}`;
        const response = await fetch(url);
        return await response.json();
    }

    renderCryptoSelect(cryptos) {
        const select = this.shadowRoot.querySelector('#cryptoSelect');
        if (select) {
            select.innerHTML = cryptos.map(crypto => `<option value="${crypto.id}">${crypto.name} - ${crypto.id}</option>`).join('');
        }
    }

    async fetchAndRenderTransactions(entryId, cryptoId) {
        try {
            const transactions = await this.fetchTransactions(entryId);
            const filteredTransactions = transactions.filter(transaction => transaction.crypto_id === cryptoId);
            this.renderTransactions(filteredTransactions);
        } catch (error) {
            console.error('Erreur lors de la récupération des transactions:', error);
            this.renderTransactions([]);  // Render an empty array in case of error
        }
    }

    async fetchTransactions(entryId) {
        const url = `/api/hassio/ingress/portfolio_crypto/fetch_transactions/${entryId}`;
        const response = await fetch(url);
        return await response.json();
    }

    async deleteCrypto(cryptoId) {
        const entryId = this.panel.config.entry_id;

        if (confirm("Êtes-vous sûr de vouloir supprimer cette crypto?")) {
            try {
                const url = `/api/hassio/ingress/portfolio_crypto/delete_crypto/${cryptoId}`;
                await fetch(url, { method: 'DELETE' });
                alert('Crypto supprimée avec succès');
                this.loadCryptos(entryId);
            } catch (error) {
                console.error('Erreur lors de la suppression de la crypto:', error);
                alert('Erreur lors de la suppression de la crypto');
            }
        }
    }

    render() {
        this.shadowRoot.innerHTML = `
        <style>
            /* Styles omitted for brevity */
        </style>
        <div class="container">
            <div class="content">
                <h1 style="color: #ffffff;">Transactions pour ${this.panel.config.entry_name}</h1>
                <div class="info">
                    <button id="exportDb">Exporter la DB</button>
                    <input type="file" id="importDb" style="display:none"/>
                    <button id="importDbButton">Importer la DB</button><br />
                    <strong>Entry ID:</strong> ${this.panel.config.entry_id}
                </div>
                <div class="select-container">
                    <select id="cryptoSelect"></select>
                    <button id="deleteCrypto" style="display:none">Supprimer la Crypto</button>
                </div>
                <div id="transactionsContainer"></div>
                <button id="add">Ajouter une transaction</button>
            </div>
        </div>
        <div id="myModal" class="modal">
            <div id="modal-content">
                <span class="close">&times;</span>
                <h2>Ajouter une nouvelle transaction</h2>
                <form id="transactionForm">
                    <label for="crypto_id">ID de la crypto:</label>
                    <input type="text" id="crypto_id" name="crypto_id" required readonly>
                    <label for="crypto_name">Nom de la crypto:</label>
                    <input type="text" id="crypto_name" name="crypto_name" required readonly>
                    <label for="quantity">Quantité:</label>
                    <input type="number" id="quantity" name="quantity" step="any" required>
                    <label for="price_usd">Prix (USD):</label>
                    <input type="number" id="price_usd" name="price_usd" step="any" required>
                    <label for="transaction_type">Type de transaction:</label>
                    <select id="transaction_type" name="transaction_type" required>
                        <option value="buy">Achat</option>
                        <option value="sell">Vente</option>
                    </select>
                    <label for="location">Lieu:</label>
                    <input type="text" id="location" name="location" required>
                    <label for="date">Date:</label>
                    <input type="date" id="date" name="date" required>
                    <button type="button" id="save">Enregistrer</button>
                </form>
            </div>
        </div>
        <div id="editModal" class="modal">
            <div id="edit-modal-content">
                <span class="close">&times;</span>
                <h2>Modifier une transaction</h2>
                <form id="editTransactionForm">
                    <input type="hidden" id="edit_transaction_id" name="transaction_id" required>
                    <label for="edit_crypto_id">ID de la crypto:</label>
                    <input type="text" id="edit_crypto_id" name="crypto_id" required readonly>
                    <label for="edit_crypto_name">Nom de la crypto:</label>
                    <input type="text" id="edit_crypto_name" name="crypto_name" required readonly>
                    <label for="edit_quantity">Quantité:</label>
                    <input type="number" id="edit_quantity" name="quantity" step="any" required>
                    <label for="edit_price_usd">Prix (USD):</label>
                    <input type="number" id="edit_price_usd" name="price_usd" step="any" required>
                    <label for="edit_transaction_type">Type de transaction:</label>
                    <select id="edit_transaction_type" name="transaction_type" required>
                        <option value="buy">Achat</option>
                        <option value="sell">Vente</option>
                    </select>
                    <label for="edit_location">Lieu:</label>
                    <input type="text" id="edit_location" name="location" required>
                    <label for="edit_date">Date:</label>
                    <input type="date" id="edit_date" name="date" required>
                    <button type="button" id="update">Mettre à jour</button>
                </form>
            </div>
        </div>
        `;

        this.shadowRoot.querySelector('#deleteCrypto').addEventListener('click', async () => {
            const selectElement = this.shadowRoot.querySelector('#cryptoSelect');
            const selectedCryptoId = selectElement.value;

            if (confirm("Êtes-vous sûr de vouloir supprimer cette crypto?")) {
                try {
                    const entryId = this.panel.config.entry_id;
                    await this._hass.callService('portfolio_crypto', 'delete_crypto', { crypto_id: selectedCryptoId, entry_id: entryId });
                    alert('Crypto supprimée avec succès');
                    this.loadCryptos(entryId);
                } catch (error) {
                    console.error('Erreur lors de la suppression de la crypto:', error);
                    alert('Erreur lors de la suppression de la crypto');
                }
            }
        });

        this.shadowRoot.querySelector('#exportDb').addEventListener('click', () => {
            this.exportDatabase();
        });

        this.shadowRoot.querySelector('#importDbButton').addEventListener('click', () => {
            this.shadowRoot.querySelector('#importDb').click();
        });

        this.shadowRoot.querySelector('#importDb').addEventListener('change', (event) => {
            const file = event.target.files[0];
            this.importDatabase(file);
        });

        this.shadowRoot.querySelector('#add').addEventListener('click', () => {
            this.openAddTransactionModal();
        });

        this.shadowRoot.querySelector('#cryptoSelect').addEventListener('change', (e) => {
            const selectedCryptoId = e.target.value;
            const selectedCryptoName = e.target.options[e.target.selectedIndex].text.split(' - ')[0];
            this.updateFormFields(selectedCryptoId, selectedCryptoName);
            this.fetchAndRenderTransactions(this.panel.config.entry_id, selectedCryptoId);
        });

        const modal = this.shadowRoot.querySelector('#myModal');
        const editModal = this.shadowRoot.querySelector('#editModal');
        const closeBtn = this.shadowRoot.querySelectorAll('.close');
        closeBtn.forEach(btn => {
            btn.onclick = function() {
                modal.style.display = 'none';
                editModal.style.display = 'none';
            };
        });
        window.onclick = function(event) {
            if (event.target == modal || event.target == editModal) {
                modal.style.display = 'none';
                editModal.style.display = 'none';
            }
        };
        this.shadowRoot.querySelector('#save').addEventListener('click', () => {
            this.saveTransaction();
        });
        this.shadowRoot.querySelector('#update').addEventListener('click', () => {
            this.updateTransaction();
        });
    }

    updateFormFields(cryptoId, cryptoName) {
        const cryptoIdField = this.shadowRoot.querySelector('#crypto_id');
        const cryptoNameField = this.shadowRoot.querySelector('#crypto_name');
        if (cryptoIdField && cryptoNameField) {
            cryptoIdField.value = cryptoId;
            cryptoNameField.value = cryptoName;
        }
    }

    renderTransactions(transactions) {
        const container = this.shadowRoot.querySelector('#transactionsContainer');
        if (!transactions || transactions.length === 0) {
            container.innerHTML = '<div>Aucune transaction trouvée.</div>';
            return;
        }

        container.innerHTML = `
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
                        <td>${transaction.transaction_id}</td>
                        <td>${transaction.crypto_name}</td>
                        <td>${transaction.quantity}</td>
                        <td>${transaction.price_usd}</td>
                        <td>${transaction.transaction_type}</td>
                        <td>${transaction.date}</td>
                        <td>
                            <button class="edit" data-id="${transaction.transaction_id}" data-crypto-id="${transaction.crypto_id}" data-crypto-name="${transaction.crypto_name}" data-quantity="${transaction.quantity}" data-price="${transaction.price_usd}" data-type="${transaction.transaction_type}" data-location="${transaction.location}" data-date="${transaction.date}">Modifier</button>
                            <button class="delete" data-id="${transaction.transaction_id}">Supprimer</button>
                        </td>
                    </tr>
                `).join('')}
            </table>
        `;

        this.shadowRoot.querySelectorAll('.delete').forEach(button => {
            button.addEventListener('click', e => {
                const transactionId = e.target.dataset.id;
                this.deleteTransaction(transactionId);
            });
        });

        this.shadowRoot.querySelectorAll('.edit').forEach(button => {
            button.addEventListener('click', e => {
                const transactionId = e.target.dataset.id;
                const cryptoId = e.target.dataset.cryptoId;
                const cryptoName = e.target.dataset.cryptoName;
                const quantity = e.target.dataset.quantity;
                const price = e.target.dataset.price;
                const type = e.target.dataset.type;
                const location = e.target.dataset.location;
                const date = e.target.dataset.date;
                this.openEditTransactionModal(transactionId, cryptoId, cryptoName, quantity, price, type, location, date);
            });
        });
    }

    openAddTransactionModal() {
        const modal = this.shadowRoot.querySelector('#myModal');
        const selectElement = this.shadowRoot.querySelector('#cryptoSelect');
        if (selectElement) {
            const selectedCryptoId = selectElement.value;
            const selectedCryptoName = selectElement.options[selectElement.selectedIndex].text.split(' - ')[0];
            this.updateFormFields(selectedCryptoId, selectedCryptoName);
        }
        modal.style.display = 'block';
    }

    openEditTransactionModal(transactionId, cryptoId, cryptoName, quantity, price, type, location, date) {
        const modal = this.shadowRoot.querySelector('#editModal');
        const transactionIdField = this.shadowRoot.querySelector('#edit_transaction_id');
        const cryptoIdField = this.shadowRoot.querySelector('#edit_crypto_id');
        const cryptoNameField = this.shadowRoot.querySelector('#edit_crypto_name');
        const quantityField = this.shadowRoot.querySelector('#edit_quantity');
        const priceField = this.shadowRoot.querySelector('#edit_price_usd');
        const typeField = this.shadowRoot.querySelector('#edit_transaction_type');
        const locationField = this.shadowRoot.querySelector('#edit_location');
        const dateField = this.shadowRoot.querySelector('#edit_date');

        transactionIdField.value = transactionId;
        cryptoIdField.value = cryptoId;
        cryptoNameField.value = cryptoName;
        quantityField.value = quantity;
        priceField.value = price;
        typeField.value = type;
        locationField.value = location;
        dateField.value = date;

        modal.style.display = 'block';
    }

    async deleteTransaction(transactionId) {
        const entryId = this.panel.config.entry_id;

        if (confirm("Êtes-vous sûr de vouloir supprimer cette transaction?")) {
            try {
                const url = `/api/hassio/ingress/portfolio_crypto/delete_transaction/${transactionId}`;
                await fetch(url, { method: 'DELETE' });
                alert('Transaction supprimée avec succès');
                const selectedCryptoId = this.shadowRoot.querySelector('#cryptoSelect').value;
                this.fetchAndRenderTransactions(entryId, selectedCryptoId);
            } catch (error) {
                console.error('Erreur lors de la suppression de la transaction:', error);
                alert('Erreur lors de la suppression de la transaction');
            }
        }
    }

    async saveTransaction() {
        const form = this.shadowRoot.querySelector('#transactionForm');
        const formData = new FormData(form);
        const transaction = {};
        formData.forEach((value, key) => {
            transaction[key] = value;
        });
        transaction.entry_id = this.panel.config.entry_id;

        try {
            const url = `/api/hassio/ingress/portfolio_crypto/save_transaction`;
            await fetch(url, { method: 'POST', body: JSON.stringify(transaction), headers: { 'Content-Type': 'application/json' } });
            alert('Transaction ajoutée avec succès');
            const selectedCryptoId = this.shadowRoot.querySelector('#cryptoSelect').value;
            this.fetchAndRenderTransactions(transaction.entry_id, selectedCryptoId);
            this.shadowRoot.querySelector('#myModal').style.display = 'none';
        } catch (error) {
            console.error('Erreur lors de l\'ajout de la transaction:', error);
            alert('Erreur lors de l\'ajout de la transaction');
        }
    }

    async updateTransaction() {
        const form = this.shadowRoot.querySelector('#editTransactionForm');
        const formData = new FormData(form);
        const transaction = {};
        formData.forEach((value, key) => {
            transaction[key] = value;
        });
        transaction.entry_id = this.panel.config.entry_id;

        try {
            const url = `/api/hassio/ingress/portfolio_crypto/update_transaction`;
            await fetch(url, { method: 'PUT', body: JSON.stringify(transaction), headers: { 'Content-Type': 'application/json' } });
            alert('Transaction mise à jour avec succès');
            const selectedCryptoId = this.shadowRoot.querySelector('#cryptoSelect').value;
            this.fetchAndRenderTransactions(transaction.entry_id, selectedCryptoId);
            this.shadowRoot.querySelector('#editModal').style.display = 'none';
        } catch (error) {
            console.error('Erreur lors de la mise à jour de la transaction:', error);
            alert('Erreur lors de la mise à jour de la transaction');
        }
    }

    async exportDatabase() {
        try {
            const url = `/api/hassio/ingress/portfolio_crypto/export_db`;
            const response = await fetch(url, { method: 'GET' });
            const blob = await response.blob();
            const urlBlob = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = urlBlob;
            a.download = 'database.db';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (error) {
            console.error('Erreur lors de l\'exportation de la base de données:', error);
            alert('Erreur lors de l\'exportation de la base de données');
        }
    }

    async importDatabase(file) {
        try {
            const url = `/api/hassio/ingress/portfolio_crypto/import_db`;
            const formData = new FormData();
            formData.append('file', file);
            await fetch(url, { method: 'POST', body: formData });
            alert('Base de données importée avec succès');
            const entryId = this.panel.config.entry_id;
            this.loadCryptos(entryId);
        } catch (error) {
            console.error('Erreur lors de l\'importation de la base de données:', error);
            alert('Erreur lors de l\'importation de la base de données');
        }
    }
}

customElements.define('crypto-transactions-panel', CryptoTransactionsPanel);
