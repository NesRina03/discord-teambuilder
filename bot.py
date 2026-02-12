import discord
import os
import random
from discord.ext import commands

# Set up intents to access member information
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_command_error(ctx, error):
    """Global error handler to see all command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore command not found errors
    print(f"Error: {type(error).__name__}: {error}")
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: {error.param.name}")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(f"Could not find member: {error.argument}")
    else:
        await ctx.send(f"An error occurred: {error}")

@bot.command()
async def hello(ctx):
    await ctx.channel.send("Hello!")

@bot.command(name="create")
async def create(ctx, subcommand: str, team_name: str, *members: discord.Member):
    """
    Creates a team with a leader and members.
    Usage: $create team TeamName @leader @member2 @member3 @member4 @member5
    """
    # Only allow command in team building channel
    TEAM_BUILDING_CHANNEL_ID = 1470905344002621573
    if ctx.channel.id != TEAM_BUILDING_CHANNEL_ID:
        await ctx.send("This command can only be used in the team building channel.")
        return
    
    guild = ctx.guild
    
    print(f"Command received! Subcommand: {subcommand}, Team: {team_name}, Members: {members}")
    
    if subcommand.lower() != "team":
        await ctx.send("Usage: `$create team TeamName @leader @member2 @member3...`")
        return
    
    # Check if team already exists (by checking if role or category exists)
    existing_role = discord.utils.get(guild.roles, name=team_name)
    existing_category = discord.utils.get(guild.categories, name=team_name)
    
    if existing_role or existing_category:
        await ctx.send(f"Team '{team_name}' already exists. Please choose a different name.")
        return
    

    # Check team size (min 3, max 5)
    if len(members) < 3:
        await ctx.send("A team must have at least 3 members (including the leader).")
        return
    
    if len(members) > 5:
        await ctx.send("A team can have a maximum of 5 members (including the leader).")
        return
    
    # Check if any member is already in another team
    # Get all team categories (team roles match category names)
    team_categories = [cat.name for cat in guild.categories]
    for member in members:
        for role in member.roles:
            # Skip generic roles like Team Leader
            if role.name in team_categories and role.name != "Team Leader":
                await ctx.send(f"{member.mention} is already in team '{role.name}'.")
                return
    
    # Check for duplicate members
    if len(members) != len(set(members)):
        await ctx.send("Each member must be unique. You cannot mention the same person twice.")
        return
    
    # Check if any member has the "Bots" role
    bots_role = discord.utils.get(guild.roles, name="Bots")
    if bots_role:
        for member in members:
            if bots_role in member.roles:
                await ctx.send(f"{member.mention} cannot be added to a team (has Bots role).")
                return
    
    
    leader = members[0]  # First tagged person is the leader
    team_members = members[1:]  # Rest are regular members
    
    # Find or create "Team Leader" role
    team_leader_role = discord.utils.get(guild.roles, name="Team Leader")
    if not team_leader_role:
        team_leader_role = await guild.create_role(
            name="Team Leader",
            color=discord.Color.gold(),
            reason="Team builder role creation"
        )
        await ctx.send(f"Created new role: Team Leader")
    
    # Create team name role
    team_role = await guild.create_role(
        name=team_name,
        color=discord.Color.from_rgb(random.randint(50, 255), random.randint(50, 255), random.randint(50, 255)),
        reason=f"Team role for {team_name}"
    )
    
    # Create category with permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        team_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, connect=True),
        leader: discord.PermissionOverwrite(
            view_channel=True,
            manage_channels=True,
            manage_permissions=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            manage_channels=True
        )
    }
    
    # Add Authors and Staff roles if they exist
    authors_role = discord.utils.get(guild.roles, name="Author")
    if authors_role:
        overwrites[authors_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, connect=True)
    
    staff_role = discord.utils.get(guild.roles, name="Staff")
    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, connect=True)
    
    category = await guild.create_category(team_name, overwrites=overwrites)
    
    # Create general text channel
    general_channel = await guild.create_text_channel(
        "general",
        category=category,
        topic=f"General chat for {team_name}"
    )
    
    # Create voice channel
    voice_channel = await guild.create_voice_channel(
        "Voice Chat",
        category=category
    )
        
    # Add both Team Leader and Team roles to the first person
    await leader.add_roles(team_leader_role, team_role)
    
    # Add only the team role to the rest of the members
    for member in team_members:
        await member.add_roles(team_role)
    
    # Send success message
    await ctx.send(f"Team '{team_name}' created successfully!")

@create.error
async def create_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found! Please mention valid members.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `$create team TeamName @leader @member2 @member3...`")

@bot.command(name="delete")
async def delete(ctx, subcommand: str, *, team_name: str):
    """
    Deletes a team, its channels, category, and role.
    Usage: $delete team TeamName
    """
    # Only allow command in team building channel
    TEAM_BUILDING_CHANNEL_ID = 1470905344002621573
    if ctx.channel.id != TEAM_BUILDING_CHANNEL_ID:
        await ctx.send("This command can only be used in the team building channel.")
        return
    
    if subcommand.lower() != "team":
        await ctx.send("Usage: `$delete team TeamName`")
        return
    
    guild = ctx.guild
    
    # Find the team role
    team_role = discord.utils.get(guild.roles, name=team_name)
    if not team_role:
        await ctx.send(f"Team '{team_name}' does not exist.")
        return
    
    # Find the category
    category = discord.utils.get(guild.categories, name=team_name)
    
    # Delete all channels in the category
    if category:
        for channel in category.channels:
            await channel.delete()
        await category.delete()
        await ctx.send(f"Deleted category and channels for '{team_name}'.")
    
    # Delete the team role
    await team_role.delete()
    await ctx.send(f"Team '{team_name}' deleted successfully!")

@delete.error
async def delete_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `$delete team TeamName`")

# Run the bot with token from environment variable
bot.run(os.getenv('DISCORD_TOKEN'))
