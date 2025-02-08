# Tournament Discord Bot

## Overview
A Discord bot built with Python that creates elimination tournaments between Discord channels. Users can vote for their favorite channels in head-to-head matchups through an automated polling system.

This project was created via [vibe coding](https://x.com/karpathy/status/1886192184808149383) and the deployment instructions are likely not correct, ask your own favorite LLM how to do it properly!

## Features
- `!tournament` command to initiate a new tournament
- Automatic channel scraping and tournament bracket generation
- Daily progression through tournament rounds
- Automated poll creation for each matchup
- Tournament progress tracking in a dedicated thread

## How it Works
1. When `!tournament` is called, the bot:
   - Scrapes all eligible channels from the server
   - Creates a tournament bracket (single elimination)
   - Creates a dedicated thread for the tournament
   - Generates first round matchups

2. For each round:
   - Creates polls for all matchups in the current round
   - Runs for 24 hours
   - Tallies votes and determines winners
   - Advances winners to next round

## Architecture
- **Discord.py**: Main library for Discord integration
- **Azure App Service**: Hosting platform

## Setup Instructions

1. Create Discord Application:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Go to "Bot" section and click "Add Bot"
   - Under "Privileged Gateway Intents", enable:
     - Message Content Intent
     - Server Members Intent

2. Get Bot Token:
   - In the Bot section, click "Reset Token" and copy your token
   - Create a `.env` file in the project root
   - Add your token: `DISCORD_TOKEN=your_token_here`

3. Invite Bot to Server:
   - Go to "OAuth2" → "URL Generator"
   - Select scopes: `bot`, `applications.commands`
   - Select permissions:
     - Manage Threads
     - Send Messages
     - Create Public Threads
     - Read Messages/View Channels
     - Add Reactions
    - permissions integer: 563276371012672
   - Copy the generated URL
   - Open URL in browser and select your server

## Infrastructure
## Deployment

### Prerequisites
1. Azure CLI installed
2. Docker Desktop installed (for local testing)
3. Access to Azure subscription

### **Create Azure Resources:**
```bash
az group create --name myResourceGroup --location eastus
az acr create --resource-group myResourceGroup --name myACR --sku Basic
az appservice plan create --name myAppServicePlan --resource-group myResourceGroup --is-linux
az webapp create --resource-group myResourceGroup --plan myAppServicePlan --name myWebApp --deployment-container-image-name myACR.azurecr.io/tournamentbot:latest
```

### Build and Deploy

1. Build and push container to ACR:
`az acr build --registry YOUR_ACR --image tournamentbot:latest .`

2. Set container on Web App:
`az webapp config container set --name YOUR_APP --resource-group YOUR_RG --container-image-name YOUR_ACR.azurecr.io/tournamentbot:latest`

redeployment, update container
3. `az webapp restart --name YOUR_APP --resource-group YOUR_RG`

monitoring
`az webapp log tail --name YOUR_APP --resource-group YOUR_RG`
