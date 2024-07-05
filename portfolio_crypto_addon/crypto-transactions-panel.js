class CryptoTransactionsPanel extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.socket = new WebSocket('ws://localhost:5000');
        this.socket.addEventListener('message', this.onMessage.bind(this));
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

    onMessage(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'cryptos_response') {
            this.renderCryptoSelect(data.cryptos);
            const selectElement = this.shadowRoot.querySelector('#cryptoSelect');
            if (selectElement) {
                const selectedCryptoId = selectElement.value;
                const selectedCryptoName = selectElement.options[selectElement.selectedIndex].text.split(' - ')[0];
                this.updateFormFields(selectedCryptoId, selectedCryptoName);
                this.fetchAndRenderTransactions(this.panel.config.entry_id, selectedCryptoId);
            }
        }
    }

    async loadCryptos(entryId) {
        this.socket.send(JSON.stringify({ type: 'fetch_cryptos', entry_id: entryId }));
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
        return await this._hass.callApi('GET', `portfolio_crypto/fetchTransactions/${entryId}`);
    }

    async deleteCrypto(cryptoId) {
        const entryId = this.panel.config.entry_id;

        if (confirm("Êtes-vous sûr de vouloir supprimer cette crypto?")) {
            try {
                await this._hass.callService('portfolio_crypto', 'delete_crypto', { crypto_id: cryptoId, entry_id: entryId });
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
            .container {
                width: 100%;
                height: 100%;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            .content {
                width: 90%;
                text-align: center;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                border: 1px solid #343a40;
            }
            th, td {
                padding: 12px;
                text-align: center;
                border-bottom: 1px solid #343a40;
            }
            th {
                background-color: black;
                color: white;
            }
            td {
                background-color: #000;
                color: white;
            }
            tr:hover td {
                background-color: #4b4e52;
            }
            button {
                margin: 10px;
                padding: 10px 20px;
                border: none;
                background-color: #007BFF;
                color: white;
                font-size: 14px;
                cursor: pointer;
                border-radius: 5px;
            }
            button:hover {
                background-color: #0056b3;
            }
            .info {
                font-size: 16px;
                margin-top: 10px;
                color: #ffffff;
            }
            #cryptoSelect {
                margin-top: 20px;
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
            }
            #myModal, #editModal {
                display: none;
                position: fixed;
                z-index: 1;
                left: 20%;
                top: 0;
                width: 100%;
                height: 100%;
                overflow: auto;
                background-color: rgb(0,0,0);
                background-color: rgba(0,0,0,0.4);
                align-items: center;
                justify-content: center;
            }
            #modal-content, #edit-modal-content {
                background-color: #000;
                padding: 20px;
                border: 1px solid #888;
                width: 50%;
                color: white;
                border-radius: 10px;
                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2), 0 6px 20px 0 rgba(0,0,0,0.19);
            }
            #transactionForm, #editTransactionForm {
                width: 100%;
            }
            #transactionForm label, #transactionForm input, #transactionForm select, #transactionForm button,
            #editTransactionForm label, #editTransactionForm input, #editTransactionForm select, #editTransactionForm button {
                width: 100%;
                box-sizing: border-box;
                margin-bottom: 10px;
            }
            .close {
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
            }
            .close:hover,
            .close:focus {
                color: #000;
                text-decoration: none;
                cursor: pointer;
            }
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
                    <button id="deleteCrypto" style="display:none" >Supprimer la Crypto</button>
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

    openAddTransactionModal() {
        const modal = this.shadowRoot.querySelector('#myModal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    openEditTransactionModal(transaction) {
        const editModal = this.shadowRoot.querySelector('#editModal');
        if (editModal) {
            const form = this.shadowRoot.querySelector('#editTransactionForm');
            form.edit_transaction_id.value = transaction.id;
            form.edit_crypto_id.value = transaction.crypto_id;
            form.edit_crypto_name.value = transaction.crypto_name;
            form.edit_quantity.value = transaction.quantity;
            form.edit_price_usd.value = transaction.price_usd;
            form.edit_transaction_type.value = transaction.transaction_type;
            form.edit_location.value = transaction.location;
            form.edit_date.value = transaction.date;
            editModal.style.display = 'flex';
        }
    }

    async saveTransaction() {
        const form = this.shadowRoot.querySelector('#transactionForm');
        const entryId = this.panel.config.entry_id;
        const data = {
            entry_id: entryId,
            crypto_name: form.crypto_name.value,
            quantity: form.quantity.value,
            price_usd: form.price_usd.value,
            transaction_type: form.transaction_type.value,
            location: form.location.value,
            date: form.date.value,
        };

        try {
            const response = await this._hass.callApi('POST', `portfolio_crypto/transaction/${entryId}`, data);
            alert('Transaction ajoutée avec succès');
            form.reset();
            this.shadowRoot.querySelector('#myModal').style.display = 'none';
            const selectElement = this.shadowRoot.querySelector('#cryptoSelect');
            const selectedCryptoId = selectElement.value;
            this.fetchAndRenderTransactions(entryId, selectedCryptoId);
        } catch (error) {
            console.error('Erreur lors de l\'ajout de la transaction:', error);
            alert('Erreur lors de l\'ajout de la transaction');
        }
    }

    async updateTransaction() {
        const form = this.shadowRoot.querySelector('#editTransactionForm');
        const entryId = this.panel.config.entry_id;
        const transactionId = form.edit_transaction_id.value;
        const data = {
            crypto_name: form.edit_crypto_name.value,
            quantity: form.edit_quantity.value,
            price_usd: form.edit_price_usd.value,
            transaction_type: form.edit_transaction_type.value,
            location: form.edit_location.value,
            date: form.edit_date.value,
        };

        try {
            const response = await this._hass.callApi('PUT', `portfolio_crypto/transaction/${entryId}/${transactionId}`, data);
            alert('Transaction mise à jour avec succès');
            form.reset();
            this.shadowRoot.querySelector('#editModal').style.display = 'none';
            const selectElement = this.shadowRoot.querySelector('#cryptoSelect');
            const selectedCryptoId = selectElement.value;
            this.fetchAndRenderTransactions(entryId, selectedCryptoId);
        } catch (error) {
            console.error('Erreur lors de la mise à jour de la transaction:', error);
            alert('Erreur lors de la mise à jour de la transaction');
        }
    }

    renderTransactions(transactions) {
        const container = this.shadowRoot.querySelector('#transactionsContainer');
        if (transactions.length === 0) {
            container.innerHTML = '<p>Aucune transaction trouvée pour cette crypto.</p>';
            return;
        }

        const rows = transactions.map(transaction => `
            <tr>
                <td>${transaction.id}</td>
                <td>${transaction.crypto_id}</td>
                <td>${transaction.crypto_name}</td>
                <td>${transaction.quantity}</td>
                <td>${transaction.price_usd}</td>
                <td>${transaction.transaction_type}</td>
                <td>${transaction.location}</td>
                <td>${transaction.date}</td>
                <td><button data-id="${transaction.id}" class="edit">Modifier</button></td>
                <td><button data-id="${transaction.id}" class="delete">Supprimer</button></td>
            </tr>
        `).join('');

        container.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>ID de la crypto</th>
                        <th>Nom de la crypto</th>
                        <th>Quantité</th>
                        <th>Prix (USD)</th>
                        <th>Type de transaction</th>
                        <th>Lieu</th>
                        <th>Date</th>
                        <th>Modifier</th>
                        <th>Supprimer</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        `;

        const editButtons = container.querySelectorAll('.edit');
        const deleteButtons = container.querySelectorAll('.delete');

        editButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                const transactionId = event.target.dataset.id;
                const transaction = transactions.find(t => t.id == transactionId);
                this.openEditTransactionModal(transaction);
            });
        });

        deleteButtons.forEach(button => {
            button.addEventListener('click', async (event) => {
                const transactionId = event.target.dataset.id;
                if (confirm("Êtes-vous sûr de vouloir supprimer cette transaction?")) {
                    try {
                        await this._hass.callApi('DELETE', `portfolio_crypto/transaction/${this.panel.config.entry_id}/${transactionId}`);
                        alert('Transaction supprimée avec succès');
                        const selectElement = this.shadowRoot.querySelector('#cryptoSelect');
                        const selectedCryptoId = selectElement.value;
                        this.fetchAndRenderTransactions(this.panel.config.entry_id, selectedCryptoId);
                    } catch (error) {
                        console.error('Erreur lors de la suppression de la transaction:', error);
                        alert('Erreur lors de la suppression de la transaction');
                    }
                }
            });
        });
    }
}

customElements.define('crypto-transactions-panel', CryptoTransactionsPanel);
