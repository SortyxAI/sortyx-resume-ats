# Sortyx Resume ATS - Deployment Guide

This guide provides the manual step-by-step process to deploy the FastAPI application securely to the internet using **Render.com** (Free Tier).

## Prerequisites
Before deploying to Render, make sure your code (including the `Dockerfile` and `docker-compose.yml`) is pushed to your GitHub repository:
```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "Add Docker deployment configuration"
git push
```

---

## Step 1: Create the Database on Render
Since the application requires PostgreSQL, we need to spin up a database first.
1. Go to [Render's Dashboard](https://dashboard.render.com/) and log in with your GitHub account.
2. Click **New +** in the top right corner and select **PostgreSQL**.
3. Fill out the database details:
   - **Name:** `sortyx-resume-db`
   - **Database / User:** Leave as default.
   - **Region:** Choose the region closest to you.
   - **Instance Type:** Select the **Free** tier.
4. Click **Create Database**.
5. **Crucial Step:** Once the database status says "Available", scroll down to the **Connections** section and copy the **Internal Database URL** (e.g., `postgres://user:password@hostname/dbname`). Save this URL; you will need it in Step 2.

---

## Step 2: Deploy the Web Service
Now, you will deploy the actual Python/FastAPI backend, which will connect to the database you just created.
1. Click **New +** in the top right corner and select **Web Service**.
2. Under "Connect a repository", search for and select your GitHub repository (`SortyxAI/sortyx-resume-ats`).
3. Fill out the service details:
   - **Name:** `sortyx-resume-api`
   - **Region:** Choose the same region you used for the Database.
   - **Environment:** Select **Docker** (Render will automatically detect the `Dockerfile` we created).
   - **Instance Type:** Select the **Free** tier.
4. Scroll down to the **Advanced** section and click **Add Environment Variable**. Add the following variables exactly as they appear in your local `.env` file:

| Key | Value |
| :--- | :--- |
| `DATABASE_URL` | Paste the **Internal Database URL** you copied in Step 1 here! |
| `GROQ_API_KEY` | *(Your actual Groq API key)* |
| `GOOGLE_DRIVE_FOLDER_ID` | `1MUhLgTIhbxH3lGGV9YrGG9zrUZ97eFpz` |
| `ADMIN_USERNAME` | `sortyx_admin` |
| `ADMIN_PASSWORD` | `Sortyx@123` |

5. Click **Create Web Service** at the bottom of the page.

## Step 3: Monitor the Build
Render will now pull your code, build the Docker container using the `Dockerfile`, and deploy it. 
You can watch the logs on the dashboard. This process usually takes 2-4 minutes.
Once you see **`Your service is live 🎉`** in the logs, you can access your completely deployed API using the `.onrender.com` link located at the top left of the dashboard.
