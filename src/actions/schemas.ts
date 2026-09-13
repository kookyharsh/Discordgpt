import { z } from 'zod';

export const GetServerInfoSchema = z.object({});
export const ListChannelsSchema = z.object({});
export const GetChannelSchema = z.object({ channelId: z.string().min(1) });
export const ListRolesSchema = z.object({});
export const GetRoleSchema = z.object({ roleId: z.string().min(1) });
export const GetMemberSchema = z.object({ userId: z.string().min(1) });

export const CreateChannelSchema = z.object({
  name: z.string().min(1).max(100),
  type: z.union([z.string(), z.number()]).optional(),
  parentId: z.string().optional(),
  topic: z.string().max(1024).optional(),
});

export const EditChannelSchema = z.object({
  channelId: z.string().min(1),
  name: z.string().min(1).max(100).optional(),
  topic: z.string().max(1024).optional(),
  parentId: z.string().optional(),
});

export const DeleteChannelSchema = z.object({
  channelId: z.string().min(1),
});

export const CreateCategorySchema = z.object({
  name: z.string().min(1).max(100),
});

export const SetChannelPermissionsSchema = z.object({
  channelId: z.string().min(1),
  overwrites: z.array(
    z.object({
      targetId: z.string().min(1),
      targetType: z.enum(['role', 'member']),
      allow: z.array(z.string()).optional(),
      deny: z.array(z.string()).optional(),
    })
  ),
});

export const CreateRoleSchema = z.object({
  name: z.string().min(1).max(100),
  color: z.number().optional(),
  permissions: z.array(z.string()).optional(),
});

export const EditRoleSchema = z.object({
  roleId: z.string().min(1),
  name: z.string().min(1).max(100).optional(),
  color: z.number().optional(),
  permissions: z.array(z.string()).optional(),
});

export const DeleteRoleSchema = z.object({
  roleId: z.string().min(1),
});

export const AssignRoleSchema = z.object({
  userId: z.string().min(1),
  roleId: z.string().min(1),
});

export const RemoveRoleSchema = z.object({
  userId: z.string().min(1),
  roleId: z.string().min(1),
});

export const TimeoutMemberSchema = z.object({
  userId: z.string().min(1),
  durationMs: z.number().positive(),
  reason: z.string().optional(),
});

export const RemoveTimeoutSchema = z.object({
  userId: z.string().min(1),
  reason: z.string().optional(),
});

export const KickMemberSchema = z.object({
  userId: z.string().min(1),
  reason: z.string().optional(),
});

export const BanMemberSchema = z.object({
  userId: z.string().min(1),
  reason: z.string().optional(),
});

export const UnbanMemberSchema = z.object({
  userId: z.string().min(1),
  reason: z.string().optional(),
});

export const SetNicknameSchema = z.object({
  userId: z.string().min(1),
  nickname: z.string().min(1).max(32),
});

export const SendMessageSchema = z.object({
  channelId: z.string().min(1),
  content: z.string().min(1).max(2000),
});

export const EditMessageSchema = z.object({
  channelId: z.string().min(1),
  messageId: z.string().min(1),
  content: z.string().min(1).max(2000),
});

export const DeleteMessageSchema = z.object({
  channelId: z.string().min(1),
  messageId: z.string().min(1),
});

export const PinMessageSchema = z.object({
  channelId: z.string().min(1),
  messageId: z.string().min(1),
});

export const UnpinMessageSchema = z.object({
  channelId: z.string().min(1),
  messageId: z.string().min(1),
});

export const BulkDeleteSchema = z.object({
  channelId: z.string().min(1),
  count: z.number().min(2).max(100),
});

export const CreateThreadSchema = z.object({
  channelId: z.string().min(1),
  name: z.string().min(1).max(100),
  autoArchiveDuration: z.number().optional(),
});

export const ArchiveThreadSchema = z.object({
  threadId: z.string().min(1),
});

export const LockThreadSchema = z.object({
  threadId: z.string().min(1),
});

export const CreateScheduleSchema = z.object({
  actionPlan: z.any(),
  scheduleType: z.string().default('cron'),
  cronExpression: z.string().min(1),
  timezone: z.string().default('UTC'),
});

export const DeleteScheduleSchema = z.object({
  scheduleId: z.string().min(1),
});

export const CreateSavedCommandSchema = z.object({
  name: z.string().min(1).max(32),
  description: z.string().min(1).max(100),
  actionPlan: z.any(),
});

export const DeleteSavedCommandSchema = z.object({
  commandId: z.string().min(1),
});
