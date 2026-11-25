# 📬 Briefkasten

![GitHub](https://img.shields.io/badge/License-MIT-brightgreen?style=for-the-badge&color=black)
[![Demo](https://img.shields.io/badge/demo-click%20here-brightgreen?style=for-the-badge&color=black)](https://briefkastenhq.com)
[![Demo](https://img.shields.io/badge/docs-click%20here-brightgreen?style=for-the-badge&color=black)](https://docs.briefkastenhq.com)

> [!NOTE]
> This is **Briefkasten v2**, a complete rewrite in SvelteKit. The previous version (v1) is available on the [`v1` branch](https://github.com/ndom91/briefkasten/tree/v1).
>
> If you were using the cloud instance, all of your data has been migrated to the new instance available at the same URL as before.

## 🚀 Getting Started

This is setup as a monorepo with **(1)** `apps/web` being a SvelteKit web application and **(2)** `apps/backend` being a Hono-based API. There are npm scripts in the root `package.json` to control most things.

1. Clone the repository

```sh
$ git clone git@github.com:ndom91/briefkasten.git && cd briefkasten
```

2. Install dependencies

```sh
$ pnpm install
```

This will install the dependencies for both apps.

3. Both `web` and `backend` need separate `.env` files. Copy both `/apps/{web,backend}/.env.example` files to `.env`, and open them with your favorite text editor to fill in your environment variables.

```sh
$ cd apps/web && cp .env.example .env
$ cd apps/backend && cp .env.example .env
```

In these environment variable files, make sure to at least fill in the `DATABASE_URL`, `BETTER_AUTH_SECRET`, `BETTER_AUTH_URL`, `PUBLIC_WORKER_URL` and one [Better Auth](https://www.better-auth.com) authentication provider, so for example `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`. The rest of the environment variables depend on the services / features you want to use.

4. Start the server!

```sh
// First time only; create the schema by applying the migrations
$ pnpm db:deploy

// dev
$ pnpm dev

// prod
$ pnpm build
$ pnpm start
```

> [!NOTE]
> `pnpm db:deploy` runs `prisma migrate deploy` against a **fresh** database. If you are upgrading an existing database whose schema already matches (e.g. a previous v2 instance), baseline it instead with `pnpm --filter sveltekasten-web exec prisma migrate resolve --applied 0_init` so the migration is recorded without re-running the DDL. For quick local iteration you can still use `pnpm db:push` to sync `schema.prisma` directly.

### Supabase Postgres

Copy the transaction and session pooler connection strings from the Supabase dashboard's **Connect** panel. Download the database CA certificate from **Database Settings → SSL Configuration**. Set the same database URLs in `apps/web/.env.local` and `apps/backend/.env.local` for local development, or in the services' `.env` files for Docker Compose. Keep the other app settings in the `.env` files described above.

```dotenv
DATABASE_URL="postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:6543/postgres?pgbouncer=true&sslmode=verify-full&sslrootcert=ENCODED_CA_PATH&schema=briefkasten"
DIRECT_URL="postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require&sslaccept=strict&sslcert=ENCODED_CA_PATH&schema=briefkasten"
```

URL-encode the database password and the absolute path to the CA certificate. For Docker Compose, mount the certificate into both services and use its path inside each container. Both URLs must use the same schema. The app uses `DATABASE_URL`, and the Prisma CLI uses `DIRECT_URL` when set. Keep `briefkasten` out of the Supabase Data API's exposed schemas because it holds application and Better Auth tables.

From the repository root, run `pnpm db:deploy` to apply the migrations to Supabase and `pnpm db:generate` to generate the Prisma clients for both apps.

## 🐋 Docker

You can run the entire stack yourself via Docker, there are multiple variants depending on if you want to self-host everything or want to rely on some cloud services.

- `docker-compose.yml` - Containers for the frontend and backend components of the application
- `docker-compose.storage.yml` - Additional `postgres` and `rustfs` containers for a database and S3-compatible object storage. You can skip these if you want to use a hosted database provider and an object storage provider, for example.

1. Run web and backend in the background

```sh
docker compose up -d
```

2. Run web and backend and additional database and object storage containers

```sh
docker compose -f docker-compose.yml -f docker-compose.storage.yml up -d
```

3. Run web and backend containers with local code mounted in for development

```sh
docker compose -f docker-compose.local-dev.yml up -d
```

4. Initialize the database

On first run you need to create the schema. The web container ships without the Prisma CLI, so apply the baseline migration directly to Postgres. If you started the bundled `database` container from `docker-compose.storage.yml`:

```sh
docker compose exec -T database \
  psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-briefkasten} \
  < apps/web/prisma/migrations/0_init/migration.sql
```

If you use an external or managed database, apply the migrations from a checkout of this repo with the dependencies installed. Prisma uses the database connection and schema configured for the web app.

```sh
pnpm db:deploy
```

## 👷 Contributing

This project is open to all contributions. Please stick to the repo settings and I'll be happy to take a look at your issue / PR!

### GitHub Actions CI

The `CI` workflow runs on branch pushes and pull requests. ESLint and Prettier check changed files, and Gitleaks scans the incoming commits. Snyk Open Source compares scans of the base and current revision and fails on new vulnerability paths. Snyk Code checks whether a finding or its data flow touches changed lines. Build and unit tests run for the whole application.

SonarQube Cloud applies the Quality Gate to code changed by a pull request. Pushes to the default branch also publish a scan to keep the baseline current. The backend unit tests publish LCOV coverage for these scans.

Under **Settings → Secrets and variables → Actions**, add `SNYK_TOKEN` and `SONAR_TOKEN` as secrets, and `SONAR_ORGANIZATION` and `SONAR_PROJECT_KEY` as variables. Enable Snyk Code in the Snyk organization and use CI-based analysis for the SonarQube Cloud project. Fork and Dependabot pull requests run code quality, Gitleaks, tests, and build. GitHub restricts access to the Actions secrets required by Snyk and SonarQube Cloud for those events.

Use `CI Result` as the required status check in the branch ruleset to enforce the combined job result.

### GitHub Releases

Open **Actions → Publish GitHub Release → Run workflow**, select `main`, and enter a tag such as `v1.1.0`. The workflow verifies that the exact commit passed the `CI Result` check on `main`, creates the tag at that commit, and publishes the GitHub Release with generated release notes.

## 📝 License

MIT
