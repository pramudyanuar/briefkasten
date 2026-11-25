import { existsSync } from "node:fs"
import path from "node:path"
import { loadEnvFile } from "node:process"
import { defineConfig } from "prisma/config"

for (const name of [".env.local", ".env"]) {
  const file = new URL(name, import.meta.url)
  if (existsSync(file)) loadEnvFile(file)
}

export default defineConfig({
  schema: path.join("prisma", "schema.prisma"),
  migrations: {
    path: path.join("prisma", "migrations"),
  },
  datasource: {
    // Use a session connection for CLI operations when a pooler is configured.
    url: process.env.DIRECT_URL || process.env.DATABASE_URL || "",
  },
})
