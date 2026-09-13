import { SlashCommandBuilder, PermissionFlagsBits } from 'discord.js';

export const promptCommand = new SlashCommandBuilder()
  .setName('prompt')
  .setDescription('Execute Discord management actions using natural language')
  .addStringOption((option) =>
    option
      .setName('request')
      .setDescription('Describe the Discord operation you want to perform')
      .setRequired(true)
  );

export const promptAuditCommand = new SlashCommandBuilder()
  .setName('prompt-audit')
  .setDescription('View recent bot management action audit logs')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild);

export const promptSchedulesCommand = new SlashCommandBuilder()
  .setName('prompt-schedules')
  .setDescription('List and manage active scheduled bot actions')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild);

export const promptSettingsCommand = new SlashCommandBuilder()
  .setName('prompt-settings')
  .setDescription('Configure server policy settings for natural language agent')
  .setDefaultMemberPermissions(PermissionFlagsBits.Administrator);

export const promptHelpCommand = new SlashCommandBuilder()
  .setName('prompt-help')
  .setDescription('Display documentation and supported actions catalog');

export const applicationCommands = [
  promptCommand,
  promptAuditCommand,
  promptSchedulesCommand,
  promptSettingsCommand,
  promptHelpCommand,
];
