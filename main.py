# Written by Kayla Gulka, 2022/08/25
# I am rushing, this will probably sloppy but as long as it works
# and is stable im not too bothered

# Last modified 2023/01/18

import discord
from discord import app_commands

from datetime import datetime
import time
import secrets
import json

import EmailHandler

intents = discord.Intents(messages=True, members=True, guilds=True)

client = discord.Client(intents=intents)
guildID = 796066586041253999
verifiedRoleID = 1013263721436545024
channelID = 1013256400891301898

# init slash commands stuff, not too sure how this works, following gist:
# https://gist.github.com/Rapptz/c4324f17a80c94776832430007ad40e6
tree = app_commands.CommandTree(client)
synced = False

emails = EmailHandler.EmailHandler()

# pending secret codes that coresponds to a user
pendingCodes = []

# {user id: [code, expiry time, macID], ...}
pendingUsers = {}

# {user id: mac id}
verifiedUsers = {}

@client.event
async def on_ready():
    global synced
    if not synced:
        await tree.sync(guild=discord.Object(id=guildID))
        synced = True
    
    print(f"Logged in as {client.user} on {datetime.now()}")
    # we will need to do some extra setup here, only server we should be working with
    # is EQ so that should hopefully make my life easier
    # LMAOOOO OR NOT SLASH COMMANDS ARE A GODSEND

@client.event
async def on_member_join(member):
    print(f'New member {member.name} joined')
    if member.id in verifiedUsers.keys():
        guild = client.get_guild(guildID)
        role = guild.get_role(verifiedRoleID)

        await member.add_roles(role)
        
    else:
        channel = client.get_channel(channelID)
        await channel.send(f'{member.mention}, welcome to the server! Please start the verification process with the `/verify` command, and check the pins for more info')

@client.event
async def on_member_remove(member):
    print(f'Member {member.name} left')
    if member.id in verifiedUsers.keys():
        verifiedUsers.pop(member.id)
        saveVerifiedUsers()

# back to slash commands
# will I ever figure out whats going on here? No!
@tree.command(name="verify", description="Verify your McMaster email with the bot", guild=discord.Object(id=guildID))
@app_commands.describe(email='Your McMaster email address')
async def verify(i:discord.Interaction, email:str):
    email=email.strip().lower()

    # validate email is mcmaster address
    emailSplit = email.split('@')

    if len(emailSplit) != 2:
        await i.response.send_message('Invalid input, try again', ephemeral=True)
    
    elif emailSplit[1] != "mcmaster.ca":
        await i.response.send_message('Not a valid McMaster address, try again', ephemeral=True)

    else:
        if i.user.id in pendingUsers.keys():
            if pendingUsers[i.user.id][1] < int(time.time()):
                # expired code
                pendingUsers.pop(i.user.id)

            else:
                await i.response.send_message('You already have a pending request! Type `/cancel` to cancel it', ephemeral=True)
                return

        if str(i.user.id) in verifiedUsers.keys():
            await i.response.send_message("You're already verified!", ephemeral=True)
            return

        print(f"Starting verification for user {i.user.name}")

        secretCode = None
        while 1:
            secretCode = secrets.token_urlsafe(32)
            if secretCode not in pendingCodes:
                # store dict with keys being user ids, values being the secret code and when it expiries (UNIX timestamp)
                pendingUsers[i.user.id] = [str(secretCode), int(time.time()) + 5*60, emailSplit[0]]
                break

        emails.sendEmail(secretCode, email)

        await i.response.send_message('Your secret code has been sent! You have 5 minutes to verify. Please make sure to check your junk email.', ephemeral=True)

@tree.command(name="code", description="Enter the secret code sent to your email to complete verification", guild=discord.Object(id=guildID))
@app_commands.describe(code="The secret code sent to your email")
async def redeemCode(i:discord.Interaction, code:str):
    code = code.strip()

    # if len(code) != 32:
    #     # invalid code length
    #     await i.response.send_message('Invalid code, try again', ephemeral=True)
    # whoops this doesn't work cause 1.3 characters per byte oooooops

    if i.user.id not in pendingUsers.keys():
        await i.response.send_message("Your username doesn't have an active code. You can get one with `/verify`", ephemeral=True)

    else:
        userInfo = pendingUsers[i.user.id]

        if userInfo[1] < int(time.time()):
            # expiried code
            await i.response.send_message("Your code is expiried! Please get a new one with `/verify`", ephemeral=True)

            pendingUsers.pop(i.user.id)

        elif userInfo[0] == code:
            # yay this user is legit
            await verifyUser(i.user.id, userInfo[2])

            await i.response.send_message("You have been verified! Please check out the rules at <#796066586825850915> next!", ephemeral=True)

        else:
            # invalid code
            await i.response.send_message("Incorrect code, try again", ephemeral=True)

@tree.command(name="cancel", description="Cancel an active verification request", guild=discord.Object(id=guildID))
async def cancel(i:discord.Interaction):
    if i.user.id not in pendingUsers.keys():
        await i.response.send_message("You don't have a pending verification attempt", ephemeral=True)
    else:
        pendingUsers.pop(i.user.id)
        print(f"Cancelled verification for user {i.user.name}")
        await i.response.send_message("Cancelled!", ephemeral=True)

@tree.command(name="manualverify", description="Manual Verification of a user through the bot (admins only)", guild=discord.Object(id=guildID))
@app_commands.describe(usr="The user to verify", macid="The user's macID")
async def manualverify(i:discord.Interaction, usr:discord.Member, macid:str):
    if i.user.id in [232230909363879939, 318125041210359808, 839040531182256148]:
        print(f"Manually verifying user {usr.name} on request of {i.user.name} with macID {macid}")
        await verifyUser(usr.id, macid)
        await i.response.send_message("The user has been verified!", ephemeral=True)

async def verifyUser(userID, macID):
    try:
        pendingUsers.pop(userID)
    except KeyError:
        pass

    verifiedUsers[str(userID)] = macID

    guild = client.get_guild(guildID)
    role = guild.get_role(verifiedRoleID)
    user = guild.get_member(userID)

    await user.add_roles(role)

    saveVerifiedUsers()

    print(f"User {user.name} verified at {datetime.now()}")
    
def saveVerifiedUsers():
    with open("verifiedUsers.json", 'w') as f:
        json.dump(verifiedUsers, f)

def loadVerifiedUsers():
    global verifiedUsers

    with open('verifiedUsers.json', 'r') as f:
        verifiedUsers = json.load(f)
    

if __name__ == "__main__":
    loadVerifiedUsers()

    with open("discordKey", 'r') as f:
        discordKey = f.readline().strip()

    client.run(discordKey)