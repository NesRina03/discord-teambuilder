import discord
import os
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
    print(f"Command received! Subcommand: {subcommand}, Team: {team_name}, Members: {members}")
    
    if subcommand.lower() != "team":
        await ctx.send("Usage: `$create team TeamName @leader @member2 @member3...`")
        return
    
    if len(members) < 1:
        await ctx.send("You must mention at least a team leader!")
        return
    
    guild = ctx.guild
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
    
    # Find or create team name role
    team_role = discord.utils.get(guild.roles, name=team_name)
    if not team_role:
        team_role = await guild.create_role(
            name=team_name,
            color=discord.Color.blue(),
            reason=f"Team role for {team_name}"
        )
        await ctx.send(f"Created new role: {team_name}")
    
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
    
    # Build response message
    member_list = ", ".join([m.mention for m in team_members]) if team_members else "No additional members"

@create.error
async def create_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found! Please mention valid members.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `$create team TeamName @leader @member2 @member3...`")

# Run the bot with token from environment variable
bot.run(os.getenv('DISCORD_TOKEN'))
