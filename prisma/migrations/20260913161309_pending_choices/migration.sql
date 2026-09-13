-- CreateTable
CREATE TABLE "PendingChoice" (
    "id" TEXT NOT NULL,
    "guildId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "params" JSONB NOT NULL,
    "field" TEXT NOT NULL,
    "options" JSONB NOT NULL,
    "prompt" TEXT NOT NULL DEFAULT '',
    "answered" BOOLEAN NOT NULL DEFAULT false,
    "expiresAt" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PendingChoice_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "PendingChoice_guildId_userId_idx" ON "PendingChoice"("guildId", "userId");

-- AddForeignKey
ALTER TABLE "PendingChoice" ADD CONSTRAINT "PendingChoice_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild"("discordGuildId") ON DELETE CASCADE ON UPDATE CASCADE;
