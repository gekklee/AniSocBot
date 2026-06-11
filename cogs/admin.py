import discord
from discord.ext import commands
from discord import app_commands
from database import db

# Create a grouping of commands for server admins
class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Create a slash command in discord to set where audit reports go
    @app_commands.command(name="setaudit", description="Set the channel for audit logs")
    # Make sure only server admins can use this command
    @app_commands.checks.has_permissions(administrator=True)
    async def set_audit_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await db.set_audit_channel(interaction.guild_id, channel.id)
        # Reply to whoever typed the command confirming the change
        await interaction.response.send_message(f"Audit log channel set to {channel.mention}", ephemeral=True)

    # Create a slash command to let certain roles give out points
    @app_commands.command(name="addmodrole", description="Allow a role to give/take points")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_mod_role(self, interaction: discord.Interaction, role: discord.Role):
        await db.add_moderator_role(interaction.guild_id, role.id)
        await interaction.response.send_message(f"Added {role.mention} as a moderator role.", ephemeral=True)

    # Create a slash command to take away the above power
    @app_commands.command(name="removemodrole", description="Remove a role's ability to give/take points")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_mod_role(self, interaction: discord.Interaction, role: discord.Role):
        # Remove the role from our database
        await db.remove_moderator_role(interaction.guild_id, role.id)
        await interaction.response.send_message(f"Removed {role.mention} from moderator roles.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))