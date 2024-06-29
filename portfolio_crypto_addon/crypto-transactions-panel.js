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
        const baseUrl = `${window.location.protocol}//${window.location.hostname}`;
        const url = `${baseUrl}:5000/load_cryptos/${entryId}`;
        

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const jsonResponse = await response.json();
            
            return jsonResponse;
        } else {
            const errorText = await response.text();
            console.error('Error response text:', errorText);
            throw new Error(`Erreur ${response.status}: ${errorText}`);
        }
    }

    renderCryptoSelect(cryptos) {
      
        const select = this.shadowRoot.querySelector('#cryptoSelect');
        if (select) {
            select.innerHTML = cryptos.map(([name, id]) => `<option value="${id}">${name} - ${id}</option>`).join('');
        }
    }

    async fetchAndRenderTransactions(entryId, cryptoId) {
        try {
            const transactions = await this.fetchTransactions(entryId);
          
           
            // Filtrer les transactions pour le crypto_id donné
            const filteredTransactions = transactions.filter(transaction => transaction[2] === cryptoId);
            
            
            
            if(filteredTransactions.length > 0){
                this.renderTransactions(filteredTransactions);
            }
            else{
                this.renderTransactions([]);
            }
            
            
        } catch (error) {
            console.error('Erreur lors de la récupération des transactions:', error);
            this.renderTransactions([]);  // Render an empty array in case of error
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
            #myModal {
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
            #modal-content {
                background-color: #000;
                padding: 20px;
                border: 1px solid #888;
                width: 50%;
                color: white;
                border-radius: 10px;
                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2), 0 6px 20px 0 rgba(0,0,0,0.19);
            }
            #transactionForm {
                width: 100%;
            }
            #transactionForm label, #transactionForm input, #transactionForm select, #transactionForm button {
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
                <h1 style="color: #ffffff;">Transactions pour ${this.panel.config.crypto_name}</h1>
                <div class="info">
                    <strong>Entry ID:</strong> ${this.panel.config.entry_id}
                </div>
                <select id="cryptoSelect"></select>
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
            this.openAddTransactionModal();
        });

        this.shadowRoot.querySelector('#cryptoSelect').addEventListener('change', (e) => {
            const selectedCryptoId = e.target.value;
            const selectedCryptoName = e.target.options[e.target.selectedIndex].text.split(' - ')[0];
            this.updateFormFields(selectedCryptoId, selectedCryptoName);
            this.fetchAndRenderTransactions(this.panel.config.entry_id, selectedCryptoId);
        });

        const modal = this.shadowRoot.querySelector('#myModal');
        const closeBtn = this.shadowRoot.querySelector('.close');
        closeBtn.onclick = function() {
            modal.style.display = 'none';
        };
        window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        };
        this.shadowRoot.querySelector('#save').addEventListener('click', () => {
            this.saveTransaction();
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
                        <td>${transaction[0]}</td>
                        <td>${transaction[1]}</td>
                        <td>${transaction[3]}</td>
                        <td>${transaction[4]}</td>
                        <td>${transaction[5]}</td>
                        <td>${transaction[7]}</td>
                        <td>
                            <button class="edit" data-id="${transaction.id}">Modifier</button>
                            <button class="delete" data-id="${transaction.id}">Supprimer</button>
                        </td>
                    </tr>
                `).join('')}
            </table>
        `;
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

    async saveTransaction() {
        const form = this.shadowRoot.querySelector('#transactionForm');
        const formData = new FormData(form);
        const transaction = {};
        formData.forEach((value, key) => {
            transaction[key] = value;
        });
        transaction.entry_id = this.panel.config.entry_id;

        try {
            const baseUrl = `${window.location.protocol}//${window.location.hostname}`;
            const url = `${baseUrl}:5000/transaction/${transaction.entry_id}`;
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(transaction)
            });

            
            if (response.ok) {
                alert('Transaction ajoutée avec succès');
                const selectedCryptoId = this.shadowRoot.querySelector('#cryptoSelect').value;
                this.fetchAndRenderTransactions(transaction.entry_id, selectedCryptoId);
                this.shadowRoot.querySelector('#myModal').style.display = 'none';
            } else {
                const errorText = await response.text();
                throw new Error(`Erreur ${response.status}: ${errorText}`);
            }
        } catch (error) {
            console.error('Erreur lors de l\'ajout de la transaction:', error);
            alert('Erreur lors de l\'ajout de la transaction');
        }
    }

    setConfig(config) {
        if (!config.entry_id || !config.integration_name) {
            throw new Error('Vous devez définir un entry_id, un crypto_id, un crypto_name, et un integration_name');
        }
        this.panel.config = config;
    }

    getCardSize() {
        return 1;
    }
}

customElements.define('crypto-transactions-panel', CryptoTransactionsPanel);
