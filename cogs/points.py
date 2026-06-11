import discord
from discord.ext import commands
from discord import app_commands
from database import db

# A helper function that makes sure someone has permission to run point commands
async def check_is_moderator(interaction: discord.Interaction):
    # Server administrators can always run these commands
    if interaction.user.guild_permissions.administrator:
        return True
        
    # Get the list of approved roles from the database
    allowed_roles = await db.get_moderator_roles(interaction.guild_id)
    if not allowed_roles:
        raise app_commands.CheckFailure("No committee roles are configured for this server.")
        
    # Check if any roles a user has match an approved role in the database
    user_role_ids = [role.id for role in interaction.user.roles]
    if any(role_id in user_role_ids for role_id in allowed_roles):
        return True
        
    # If no permissions checks were passed, send error message
    raise app_commands.CheckFailure("You do not have permission to run this command.")

# A group for all standard point commands
class PointsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Tool for sending audit messages to the correct channel with a consistent format
    async def log_audit(self, guild: discord.Guild, target: discord.Member, admin: discord.Member, amount: int, reason: str, new_total: int):
        channel_id = await db.get_audit_channel(guild.id)
        # If no channel is set, stop as this is not a required feature
        if not channel_id:
            return
            
        # Get the actual channel channel object from discord
        channel = guild.get_channel(channel_id)
        # If the channel was deleted, stop
        if not channel:
            return
            
        # Create an embedded message and colour it green for points added, red for points lost
        embed = discord.Embed(title="Points Updated", color=discord.Color.green() if amount > 0 else discord.Color.red())
        embed.add_field(name="Member", value=target.mention, inline=True)
        embed.add_field(name="Moderator", value=admin.mention, inline=True)
        embed.add_field(name="Change", value=f"{amount:+d}", inline=True)
        embed.add_field(name="New Total", value=str(new_total), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # Slash command to look up points
    @app_commands.command(name="points", description="Check points for yourself or another member")
    async def view_points(self, interaction: discord.Interaction, target: discord.Member = None):
        # If the user didn't list a target, assume they want to check their own score
        target = target or interaction.user
        points = await db.get_points(interaction.guild_id, target.id)
        await interaction.response.send_message(f"{target.mention} has **{points}** points.")

    # Slash command to see who is winning
    @app_commands.command(name="leaderboard", description="View the top point earners")
    async def leaderboard(self, interaction: discord.Interaction):
        results = await db.get_leaderboard(interaction.guild_id)
        if not results:
            await interaction.response.send_message("No points have been awarded yet.")
            return
            
        # Create an embed
        embed = discord.Embed(title="Leaderboard", color=discord.Color.gold())
        
        # Build out a list of the top member
        description = []
        for index, (user_id, points) in enumerate(results, start=1):
            description.append(f"**{index}.** <@{user_id}> - {points} points")
            
        # Attach list to the message body and separate items by new lines
        embed.description = "\n".join(description)
        await interaction.response.send_message(embed=embed)

    # Slash command for committee to give somebody points
    @app_commands.command(name="addpoints", description="Add points to a member")
    # Run helper function first to make sure they are allowed
    @app_commands.check(check_is_moderator)
    async def add_points(self, interaction: discord.Interaction, target: discord.Member, amount: int, reason: str):
        # Catch mistakes like trying to add 0 or negative points
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)
            return
            
        # Add the points in the database and get the member's new total points
        new_total = await db.add_points(interaction.guild_id, target.id, interaction.user.id, amount, reason)
        # Call audit function
        await self.log_audit(interaction.guild, target, interaction.user, amount, reason, new_total)
        
        # Inform the committee who ran the command
        await interaction.response.send_message(f"Added {amount} points to {target.mention} for '{reason}'. New total: {new_total}.")

    # Slash command for committee to remove a member's points
    @app_commands.command(name="removepoints", description="Remove points from a member")
    @app_commands.check(check_is_moderator)
    async def remove_points(self, interaction: discord.Interaction, target: discord.Member, amount: int, reason: str):
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)
            return
            
        # We pass -amount to the database to remove points
        new_total = await db.add_points(interaction.guild_id, target.id, interaction.user.id, -amount, reason)
        await self.log_audit(interaction.guild, target, interaction.user, -amount, reason, new_total)

        await interaction.response.send_message(f"Removed {amount} points from {target.mention} for '{reason}'. New total: {new_total}.")

    # Error catchers if someone fails the check_is_moderator test
    @add_points.error
    @remove_points.error
    async def mod_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(str(error), ephemeral=True)
        # Otherwise, generic message
        else:
            await interaction.response.send_message("An error occurred.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PointsCog(bot))