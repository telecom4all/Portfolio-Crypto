# Portfolio Crypto
![Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/exemple.png)
## Introduction

L'intégration "Portfolio Crypto" permet de gérer et surveiller vos investissements en cryptomonnaie directement depuis Home Assistant. Cette intégration utilise l'API CoinGecko pour récupérer les informations sur les cryptomonnaies et fournit une interface simple pour suivre vos investissements.

## Fonctionnalités

- **Gestion des Portfolios** : Suivez plusieurs portfolios de cryptomonnaies.
- **Ajout/Suppression de Cryptomonnaies** : Ajoutez ou supprimez des cryptomonnaies de votre portfolio.
- **Suivi des Transactions** : Enregistrez et suivez vos transactions d'achat et de vente.
- **Calcul des Profits et Pertes** : Calculez automatiquement vos profits et pertes pour chaque cryptomonnaie.
- **Icônes Personnalisées** : Affichez des icônes uniformes pour toutes les cryptomonnaies.

## Installation

### Pré-requis

- Home Assistant installé et configuré
- Accès à l'interface de Home Assistant

### Étapes d'installation Addon

1. Accédez à votre interface Home Assistant.
2. Cliquez sur `Paramètres` dans le menu de gauche.
3. Sélectionnez `Modules complémentaires` puis cliquez sur `Boutique des modules complémentaires` et cliquez sur l'icone avec les 3 point en haut à droite, puis cliquez sur `Dépots`.
   ![Modules complémentaires](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/1.png)
3. Ajoutez l'adresse :  `https://github.com/telecom4all/Portfolio-Crypto` et cliquez sur `Ajouter`.
   ![Installer Repo Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/2.png)   
4. Rafraîchissez le cache du navigateur `CTRL-F5`.
5. Recherchez `Portfolio Crypto` et cliquez sur `Installer`.
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/4.png)
   ![Installer Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/5.png)
6. Démarez `Portfolio Crypto` et cliquez sur `Chien de Garde`.
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/6.png)
7. Aller dans  `Journal`, actualisez jusqu'au moment ou vous verrez `Insatallation est terminée ...` 
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/8.png)
8. Redémarrez `Homeassisant`
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/9.png)


### Étapes d'installation Intégration

1. Accédez à `Paramètres` - `Appareils et Services`.
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/10.png)
2. Cliquez sur `Ajouter une intégration` et recherchez `Portfolio Crypto` cliquez dessus pour l'installer.
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/12.png)
3. Donner un nom a votre `Portefeuille` 
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/13.png)
4. Vous verrez l'intégration `Portfolio Crypto` la liste et un nouveau panel dans la sidebar
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/15.png)


## Configuration
### Ajouter une Cryptomonnaie

1. Une Fois dans votre `Portefeuille` cliquer sur `configurer` pour ajouter une `crypto`
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/16.png)

2. Rentrez `l'id coingecko` ou le `nom de la crypto` que vous voulez ajouter puis  `Portefeuille` cliquer sur `Valider` pour rechercher le bon id sur coingecko
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/17.png)

3. Vérifiez que le `nom` et l'`id` a bien été trouvé et cliquez sur `valider` pour ajouter la crypto
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/18.png)

4. cliquez sur l'icone avec les 3 point du `portefeuille` pour recharger l'intégration (a faire a chaque fois que l'on ajoute une crypto)
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/20.png)

5. Vous pourrez voir les `entités` qui on été crée
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/29.png)

6. Vous pourrez voir les `appareils` qui on été crée
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/31.png)

### Configurer l'ingress et l'url externe

1. Modifier votre `configuration.yaml`, un bout de code a été ajouter 
    modifiez `external_url` selon votre configuration :

    ```yaml
    homeassistant:
        external_url: "https://domain"
    ```
 
    

5. Redémarez `homeassistant` pour prendre en compte les modification 
   ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/40.png)


## Utilisation

### Suivi des Transactions

L'intégration "Portfolio Crypto" permet de suivre toutes vos transactions d'achat et de vente pour chaque cryptomonnaie.

- **Ajouter une Transaction** :

    Utilisez le panneau personnalisé pour ajouter une nouvelle transaction. Vous devrez fournir les informations suivantes :
    - ID de la cryptomonnaie
    - Nom de la cryptomonnaie
    - Quantité
    - Prix (USD)
    - Type de transaction (achat ou vente)
    - Lieu
    - Date

    ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/41.png)
    ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/42.png)
    ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/44.png)

- **Modifier une Transaction** :

    Sélectionnez une transaction existante et modifiez les informations selon vos besoins.

- **Supprimer une Transaction** :

    Supprimez une transaction en utilisant le panneau personnalisé.

- **Exportez votre fichier de base de donnée sql** :

    Cliquez sur le boutton `Exporter Db` cela téléchargera cotre db sur votre ordinateur.
    ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/46.png)

- **Importez votre fichier de base de donnée sql** :

    Cliquez sur le boutton `Importer Db` et aller chercher votre fichier sur l'ordinateur.
    ![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/47.png)

### Calcul des Profits et Pertes

L'intégration calcule automatiquement vos profits et pertes basés sur les transactions enregistrées. 

Les informations suivantes sont disponibles pour le portefeuille:
- Investissement Total
- Valeur Actuelle
- Profit/Perte Total
- Pourcentage de Profit/Perte
- Nombre de transactions

Les informations suivantes sont disponibles pour le portefeuille:
- Investissement Total
- Valeur Actuelle
- Profit/Perte Total
- Pourcentage de Profit/Perte
- Nombre de transactions
- prix d'achat moyen

![Rechercher Portfolio Crypto](https://raw.githubusercontent.com/telecom4all/Portfolio-Crypto/main/images/49.png)

## Dépannage

### Problèmes de Connexion

Si vous rencontrez des problèmes de connexion avec l'API CoinGecko, assurez-vous que votre instance Home Assistant a accès à Internet et que toutes les dépendances sont correctement installées.

### Erreurs de Base de Données

Si vous rencontrez des erreurs liées à la base de données, vérifiez les logs de Home Assistant et assurez-vous que les bases de données sont correctement initialisées et accessibles.


## Contribution

Les contributions sont les bienvenues ! Si vous souhaitez contribuer à ce projet, veuillez suivre ces étapes :

- Forkez le dépôt sur GitHub.

- Créez une branche pour votre fonctionnalité ou correction de bug.

- Soumettez une pull request avec une description détaillée de vos modifications.


Merci d'utiliser "Portfolio Crypto" pour Home Assistant. Nous espérons que cette intégration vous aidera à mieux gérer et suivre vos investissements en cryptomonnaie.

## Soutien

Ce code est disponible pour tous si vous voulez me "soutenir :-)" voici un lien d'affiliation Bitget : https://partner.bitget.com/bg/85MZE2

ou en cryptos :

- BTC --> 1CetuWt9PuppZ338MzBzQZSvtMW3NnpjMr
- ETH (Réseau ERC20) --> 0x18f71abd7c2ee05eab7292d8f34177e7a1b62236
- MATIC (Réseau Polygon) --> 0x18f71abd7c2ee05eab7292d8f34177e7a1b62236
- BNB (Réseau BSC BEP20) --> 0x18f71abd7c2ee05eab7292d8f34177e7a1b62236
- SOL --> AsLvBCG1fpmpaueTYBmU5JN5QKVkt9a1dLR44BAGUZbV