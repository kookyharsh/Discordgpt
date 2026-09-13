import { SlashCommandBuilder } from 'discord.js';

export const STABLE_SLASH_COMMANDS = [
  new SlashCommandBuilder()
    .setName('prompt')
    .setDescription('Execute natural language Discord management action')
    .addStringOption((opt) => opt.setName('input').setDescription('Describe your desired Discord operation').setRequired(true)),

  new SlashCommandBuilder()
    .setName('prompt-audit')
    .setDescription('View recent automated action audit log for this server'),

  new SlashCommandBuilder()
    .setName('prompt-revoke')
    .setDescription('Revoke an automated task or schedule')
    .addStringOption((opt) => opt.setName('id').setDescription('Schedule ID to revoke').setRequired(true)),

  new SlashCommandBuilder()
    .setName('prompt-schedules')
    .setDescription('List all active automated schedules for this server'),

  new SlashCommandBuilder()
    .setName('prompt-settings')
    .setDescription('View or update server automation policy settings'),

  new SlashCommandBuilder()
    .setName('prompt-help')
    .setDescription('Learn how to use DiscordGPT natural language instructions'),
];
