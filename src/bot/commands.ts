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
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
  .addStringOption((option) =>
    option
      .setName('cancel_id')
      .setDescription('Cancel a scheduled job by its ID (see the list first)')
      .setRequired(false)
  );

export const promptSettingsCommand = new SlashCommandBuilder()
  .setName('prompt-settings')
  .setDescription('Configure server policy settings for natural language agent')
  .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
  .addStringOption((option) =>
    option
      .setName('key')
      .setDescription('Setting to change')
      .setRequired(false)
      .addChoices(
        { name: 'enabled', value: 'enabled' },
        { name: 'timezone', value: 'timezone' },
        { name: 'allowed_actions', value: 'allowed_actions' },
        { name: 'disabled_actions', value: 'disabled_actions' }
      )
  )
  .addStringOption((option) =>
    option
      .setName('value')
      .setDescription('New value (e.g. false, America/New_York, create_channel,send_message)')
      .setRequired(false)
  );

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
