-- CreateTable
CREATE TABLE "PendingQuestion" (
    "id" TEXT NOT NULL,
    "guildId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "channelId" TEXT,
    "question" TEXT NOT NULL,
    "originalPrompt" TEXT NOT NULL,
    "answered" BOOLEAN NOT NULL DEFAULT false,
    "expiresAt" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PendingQuestion_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "PendingQuestion_guildId_userId_idx" ON "PendingQuestion"("guildId", "userId");

-- AddForeignKey
ALTER TABLE "PendingQuestion" ADD CONSTRAINT "PendingQuestion_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild"("discordGuildId") ON DELETE CASCADE ON UPDATE CASCADE;
