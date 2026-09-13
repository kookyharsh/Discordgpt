-- DropForeignKey
ALTER TABLE "ActionExecution" DROP CONSTRAINT "ActionExecution_guildId_fkey";

-- DropForeignKey
ALTER TABLE "AuditLog" DROP CONSTRAINT "AuditLog_guildId_fkey";

-- DropForeignKey
ALTER TABLE "ConfirmationRequest" DROP CONSTRAINT "ConfirmationRequest_guildId_fkey";

-- DropForeignKey
ALTER TABLE "Conversation" DROP CONSTRAINT "Conversation_guildId_fkey";

-- DropForeignKey
ALTER TABLE "GeneratedCommand" DROP CONSTRAINT "GeneratedCommand_guildId_fkey";

-- DropForeignKey
ALTER TABLE "GuildSettings" DROP CONSTRAINT "GuildSettings_guildId_fkey";

-- DropForeignKey
ALTER TABLE "ScheduledAction" DROP CONSTRAINT "ScheduledAction_guildId_fkey";

-- AddForeignKey
ALTER TABLE "GuildSettings" ADD CONSTRAINT "GuildSettings_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild"("discordGuildId") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Conversation" ADD CONSTRAINT "Conversation_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild"("discordGuildId") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ActionExecution" ADD CONSTRAINT "ActionExecution_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild"("discordGuildId") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ScheduledAction" ADD CONSTRAINT "ScheduledAction_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild"("discordGuildId") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "GeneratedCommand" ADD CONSTRAINT "GeneratedCommand_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild"("discordGuildId") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AuditLog" ADD CONSTRAINT "AuditLog_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild"("discordGuildId") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ConfirmationRequest" ADD CONSTRAINT "ConfirmationRequest_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild"("discordGuildId") ON DELETE CASCADE ON UPDATE CASCADE;
