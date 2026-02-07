import discord
import os
import json
from io import BytesIO
from PIL import Image, ImageFilter
import imagehash
from dotenv import load_dotenv
import gc
from memory_profiler import profile

import asyncpg

from db import UserIdMapper
from myCrypter import myCrypter
from constants import (
    MASKBIT_ROW,
    MASKBIT_COLUMN,
    MASKBIT_LENGTH_NUM,
    MASKBIT_LENGTH_CHECKSUM,
    MASK_BASE,
    MASK_COLOR,
    TEXT_COLOR,
    INTER_ID_BUTTONCLICK_IMAGEVIEW,
    INTER_ID_BUTTONCLICK_IMAGEREMOVE,
    INTER_ID_BUTTONCLICK_IMAGEREMOVEYES,
    INTER_ID_BUTTONCLICK_IMAGEREMOVENO,
    EMOJI_BUTTON_PREVIOUS,
    EMOJI_BUTTON_NEXT,
    EMOJI_EYES,
    EMOJI_TRASHCAN,
    KEY_ID,
    KEY_THREAD_ID,
    KEY_AUTHOR_ID,
)

# 開発時に環境変数をロード
try:
    load_dotenv()
except Exception as e:
    print(e)

TOKEN = os.getenv("TOKEN")
ID_ROOM_BOT = int(os.getenv("ID_ROOM_BOT"))
ID_ROOM_VIEW = int(os.getenv("ID_ROOM_SHOMIN"))  # 投稿された画像が表示される
ID_ROOM_PIC = int(os.getenv("ID_ROOM_PIC"))  # 投稿する画像を投稿する
DATABASE_URL = os.getenv("DATABASE_URL")

user_id_mapper: UserIdMapper = None

# discord.pyの処理

intents = discord.Intents.default()  # 標準設定から
intents.typing = False  # typingは受け取らない
intents.message_content = True  # message_contentは受け取る
intents.members = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

#############


class myView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


class myUploader:
    """画像をDiscordのテキストチャンネルにアップロードするためのクラス。

    このクラスは、指定されたbotroomに画像をアップロードし、
    別の指定されたchatroomに通知を送信します。

    Attributes:
        botroom (discord.TextChannel): 画像がボットによって保管されるチャンネル。
        chatroom (discord.TextChannel): 画像のアップロード通知が送信されるチャンネル。
        id_author (str): 画像をアップロードしたユーザーの固有ID。
        embed1 (discord.Embed): メッセージをフォーマットするための埋め込みオブジェクト。

    メソッド:
        __init__(botroom: discord.TextChannel, chatroom: discord.TextChannel):
            指定されたボットルームとチャットルームでmyUploaderクラスを初期化します。
        setComment(comment: str) -> 'myUploader':
            アップロードする画像に付属するコメントを設定します。
        setTitle(title: str) -> 'myUploader':
            アップロードする画像のタイトルを設定します。
        setAuthor(id: str) -> 'myUploader':
            画像をアップロードしたユーザーの固有IDを設定します。
        setSendChannel(c: discord.TextChannel) -> 'myUploader':
            画像のアップロード通知が送信されるチャンネルを設定します。
        upload(files: list[discord.File], parameter: dict = None):
            画像をbotroomにアップロードし、chatroomに通知を送信します。
    """

    botroom: discord.TextChannel
    chatroom: discord.TextChannel
    id_author: str
    embed1: discord.Embed

    def __init__(self, botroom: discord.TextChannel, chatroom: discord.TextChannel):
        """myUploaderクラスを初期化します。

        Args:
            botroom (discord.TextChannel): 画像がボットによって保管されるチャンネル。
            chatroom (discord.TextChannel): 画像のアップロード通知が送信されるチャンネル。
        """
        self.botroom = botroom
        self.chatroom = chatroom
        self.embed1 = discord.Embed(color=discord.Colour.blue())
        self.embed1.set_footer(text="削除ボタンは投稿者のみ有効です")

    def setComment(self, comment: str):
        """アップロードする画像に付属するコメントを設定します。

        Args:
            comment (str): 付属するコメント。

        Returns:
            myUploader: 現在のmyUploaderクラスのインスタンス。
        """
        self.embed1.description = comment
        return self

    def setTitle(self, title: str):
        """アップロードする画像のタイトルを設定します。

        Args:
            title (str): 設定するタイトル。

        Returns:
            myUploader: 現在のmyUploaderクラスのインスタンス。
        """
        self.embed1.title = title
        return self

    def setAuthor(self, id: str):
        """画像をアップロードしたユーザーの固有IDを設定します。

        Args:
            id (str): ユーザーの固有ID。

        Returns:
            myUploader: 現在のmyUploaderクラスのインスタンス。
        """
        self.id_author = id
        return self

    def setSendChannel(self, c: discord.TextChannel):
        """画像のアップロード通知が送信されるチャンネルを設定します。

        Args:
            c (discord.TextChannel): 通知を送信するチャンネル。

        Returns:
            myUploader: 現在のmyUploaderクラスのインスタンス。
        """
        self.chatroom = c
        return self

    async def upload(self, files: list[discord.File], parameter: dict = {}):
        """画像をbotroomにアップロードし、chatroomに通知を送信します。

        このメソッドは、指定されたbotroomへの画像の処理とアップロードを行います。
        また、画像のぼかしプレビュー、コメント、作者情報を含む通知をchatroomに送信します。

        アップロードプロセスは主に以下の2つの作業を行います:
        1. アップロードされた画像を保管するためにbotroomに専用のスレッドを作成します。
        2. chatroomに画像のプレビュー、製作者、コメントを含むembedを投稿します。

        Args:
            files (list[discord.File]): アップロードするファイルのリスト。
            parameter (dict, optional): カスタムアクションのための追加パラメータ。デフォルトはNone。

        例:
            uploader = myUploader(botroom, chatroom)
            uploader.setComment("これはコメントです")
                   .setTitle("画像のタイトル")
                   .setAuthor("AuthorID")
                   .upload([file], parameter={"key": "value"})
        """
        thread = await self.botroom.create_thread(
            name=files[0].filename, auto_archive_duration=60
        )
        thread_id = thread.id
        msg_in_botroom = await thread.send(None, files=files)
        attachment = msg_in_botroom.attachments[0]

        im = file2image(files[0])
        # intensity = 30
        # minlength = 40
        # if im.width > im.height:
        #     smallwidth = min(math.ceil(im.width / intensity),minlength)
        #     imsmall = im.resize((smallwidth, math.ceil(im.height / im.width * smallwidth)))
        # else:
        #     smallheight = min(math.ceil(im.height / intensity),minlength)
        #     imsmall = im.resize((smallheight, math.ceil(im.width / im.height * smallheight)))
        # blur:Image = imsmall.resize((im.width,im.height),resample=Image.Resampling.NEAREST).filter(ImageFilter.GaussianBlur(100)).point(lambda x:x*0.5)
        blur: Image.Image = im.filter(ImageFilter.GaussianBlur(100))
        blurfile = image2file(blur)

        if parameter:
            custom_id_viewing_dict = parameter.copy()
            custom_id_removing_dict = parameter.copy()
        else:
            custom_id_viewing_dict = {}
            custom_id_removing_dict = {}

        custom_id_viewing_dict["id"] = str(INTER_ID_BUTTONCLICK_IMAGEVIEW)
        custom_id_viewing_dict["thread_id"] = thread_id
        custom_id_viewing = json.dumps(custom_id_viewing_dict)

        custom_id_removing_dict["id"] = str(INTER_ID_BUTTONCLICK_IMAGEREMOVE)
        custom_id_removing_dict["thread_id"] = thread_id
        custom_id_removing_dict["author_id"] = self.id_author
        custom_id_removing = json.dumps(custom_id_removing_dict)

        self.embed1.set_image(url=f"attachment://{blurfile.filename}")
        self.embed1.add_field(name=" ", value="{}枚の画像".format(len(files)))

        components = discord.ui.View(timeout=None)
        components.add_item(
            item=discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                emoji=EMOJI_EYES,
                label="閲覧する",
                custom_id=custom_id_viewing,
            )
        )
        components.add_item(
            item=discord.ui.Button(
                style=discord.ButtonStyle.red,
                emoji=EMOJI_TRASHCAN,
                label="画像の削除",
                custom_id=custom_id_removing,
            )
        )
        await self.chatroom.send(
            None, file=blurfile, embed=self.embed1, view=components
        )


class myViewforUploadImage(discord.ui.View):
    def __init__(
        self,
        original_message: discord.Message,
        files: list[discord.File],
        uploader: myUploader,
    ):
        super().__init__(timeout=None)
        self.files = files
        self.uploader = uploader
        self.original_message = original_message
        self.willdelete = True
        # #self.add_item(mySelectListSpoiler())
        # #self.add_item(myTextInputforUploadComment())
        # self.add_item(myButtonforUploadImage(files,uploader))

    # @discord.ui.select(cls=discord.ui.ChannelSelect,placeholder="投稿するチャンネルを選択",channel_types=[discord.ChannelType.text])
    # async def select_channels(self,ctx:discord.Interaction,select:discord.ui.ChannelSelect):
    #     print(ctx.data.values)
    #     print(select.values)
    #     self.uploader.setSendChannel(ctx.guild.get_channel(select.values[0].id))
    #     await ctx.response.defer()

    # @discord.ui.select(
    #     cls=discord.ui.Select,
    #     options=[
    #         discord.SelectOption(
    #             label="投稿後、元画像を自動で削除する", value="True", default=True
    #         ),
    #         discord.SelectOption(
    #             label="投稿後、元画像を自動で削除しない", value="False"
    #         ),
    #     ],
    #     placeholder="元画像を削除しますか？",
    # )
    async def delete(self, ctx: discord.Interaction, select: discord.ui.Select):
        if ctx.user.id != self.original_message.author.id:
            await ctx.response.send_message(
                content=None,
                embed=discord.Embed(title="エラー", color=0xFF0000).add_field(
                    name="警告", value="この操作は投稿者にしか行えません。"
                ),
            )
            return
        if select.values[0] == "True":
            self.willdelete = True
        else:
            self.willdelete = False
        await ctx.response.defer()

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="投稿する")
    async def upload(self, ctx: discord.Interaction, select: discord.ui.Button):
        if ctx.user.id != self.original_message.author.id:
            await ctx.response.send_message(
                content=None,
                embed=discord.Embed(title="エラー", color=0xFF0000).add_field(
                    name="警告", value="この操作は投稿者にしか行えません。"
                ),
            )
            return
        if self.willdelete:
            await self.original_message.delete()
        await ctx.response.send_modal(
            myModalforUploadImage(files=self.files, uploader=self.uploader)
        )
        select.disabled = True
        await ctx.edit_original_response(
            content="画像を投稿中です...", view=select.view
        )
        # await self.uploader.upload(self.files)
        await ctx.delete_original_response()


# class myButtonforUploadImage(discord.ui.Button):
#     def __init__(self,  files:list[discord.File], uploader:myUploader, style: discord.ButtonStyle = discord.ButtonStyle.secondary, label="投稿する"):
#         super().__init__(style=style, label=label)
#         self.files = files
#         self.uploader = uploader
#     async def callback(self, ctx: discord.Interaction):
#         await ctx.response.send_modal(myModalforUploadImage(files=self.files,uploader=self.uploader))
#         self.disabled = True
#         await ctx.edit_original_response(content="画像を投稿中です...",view=self.view)
#         #await self.uploader.upload(self.files)
#         await ctx.delete_original_response()


class myModalforUploadImage(discord.ui.Modal):
    def __init__(self, files: list[discord.File], uploader: myUploader):
        super().__init__(
            title="投稿",
            timeout=None,
        )
        self.files = files
        self.uploader = uploader

        # self.title = discord.ui.InputText(
        #     label="タイトル",
        #     style=discord.TextStyle.short,
        #     placeholder="",
        #     required=False,
        # )
        self.comment = discord.ui.TextInput(
            label="コメント(100文字以内)",
            style=discord.TextStyle.short,
            placeholder="",
            required=False,
        )
        self.add_item(self.comment)  # .add_item(mySelectListSpoiler())

    async def on_submit(self, ctx: discord.Interaction):
        await ctx.response.send_message("画像を投稿しています...", ephemeral=True)
        if len(self.comment.value) > 100:
            await ctx.edit_original_response(
                content="コメントは100文字以内にしてください。"
            )
            return
        await self.uploader.setComment(self.comment.value).upload(self.files)
        await ctx.edit_original_response(content="投稿しました。")


class myButtonforImageView(discord.ui.Button):
    def __init__(
        self,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        thread=discord.Thread,
        label="閲覧する",
    ):
        super().__init__(style=style, label=label)
        self.thread = thread

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "画像を送信しています...", ephemeral=True
        )
        async for m in self.thread.history(oldest_first=True, limit=1):
            file = await m.attachments[0].to_file()
        mycrypter = myCrypter(file2image(file))
        internal_id = await user_id_mapper.get_or_create_internal_id(interaction.user.id)
        mycrypter.setChannel([True, False, False, True]).encryptByID(internal_id).setChannel(
            [False, False, True, True]
        ).encryptByLabel(interaction.user.name)
        encryptedfile = image2file(mycrypter.executeEncryption())
        msg: discord.Message = await self.thread.send(file=encryptedfile)
        await interaction.edit_original_response(content=msg.attachments[0].url)
        print(f"view id->{internal_id}")


class myButtonforImageViewbyUrl(discord.ui.Button):
    def __init__(
        self,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        label="閲覧する",
        image_url: str,
    ):
        super().__init__(style=style, label=label, url=image_url)


class mySelectListSpoiler(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="スポイラーを表示しますか？",
            custom_id=str(self.__hash__()),
            options=[
                discord.SelectOption(label="はい", value="はい", description=""),
                discord.SelectOption(label="いいえ", value="いいえ", description=""),
            ],
        )

    async def callback(self, ctx: discord.Interaction):
        print(self.values)
        self.placeholder = self.values[0]
        await ctx.response.edit_message(view=self.view)


class myTextInputforUploadComment(discord.ui.TextInput):
    def __init__(self):
        super().__init__(
            label="コメント", placeholder="画像に添付するコメントを入力してください。"
        )


####################


async def createMyUploader(
    id_botroom: str, id_chatroom: str, ctx: discord.interactions.Interaction
):
    botroom: discord.TextChannel = await ctx.guild.fetch_channel(id_botroom)
    chatroom: discord.TextChannel = await ctx.guild.fetch_channel(id_chatroom)
    myuploader = myUploader(botroom, chatroom)
    return myuploader


# @profile
def file2image(file: discord.File) -> Image.Image:
    im = Image.open(file.fp)
    file.fp.seek(0)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    return im


# @profile
def image2file(image: Image.Image) -> discord.File:
    fileio = BytesIO()
    image.save(fileio, format="png")
    fileio.seek(0)
    hash = imagehash.average_hash(image)
    file = discord.File(fileio, filename=f"{hash}.png")
    return file


@client.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return
    if msg.channel.id == ID_ROOM_PIC:
        if len(msg.attachments) > 0:
            await processImageUpload(msg)


async def processImageUpload(msg: discord.Message, ctx: discord.Interaction = None):
    botroom: discord.TextChannel = await msg.guild.fetch_channel(ID_ROOM_BOT)
    chatroom: discord.TextChannel = await msg.guild.fetch_channel(ID_ROOM_VIEW)
    myuploader = myUploader(botroom, chatroom)
    myuploader.setTitle(
        f"{msg.author.display_name}さんの画像がアップロードされました"
    ).setAuthor(str(msg.author.id))
    files = [await s.to_file() for s in msg.attachments]
    components = myViewforUploadImage(msg, files, myuploader)
    if ctx:
        await ctx.response.send_message(
            content="画像を投稿します。", view=components, ephemeral=True
        )
    else:
        await msg.reply(content="画像を投稿します。", view=components)


# @profile
@client.event
async def on_interaction(ctx: discord.Interaction):
    print(ctx.data)
    if ctx.data.get("component_type") == 2:
        d = ctx.data.get("custom_id")
        try:
            d = json.loads(d)
        except json.JSONDecodeError:
            return  # JSON形式でない場合はスキップ（コールバックメソッドが処理）

        print(d)
        if d.get("id") == "check":
            await ctx.response.send_message(
                "{}さん、こんにちは！".format(ctx.user.display_name)
            )
        if d.get("id") == str(INTER_ID_BUTTONCLICK_IMAGEVIEW):  # buttonclick_imageview
            await processButtonclickImageView(ctx, d.get("thread_id"))
        if d.get("id") == str(
            INTER_ID_BUTTONCLICK_IMAGEREMOVE
        ):  # buttonclick_imageremove
            await processButtonclickImageRemove(ctx, d)
        # if d.get("id") == str(INTER_ID_BUTTONCLICK_IMAGEREMOVEYES):
        #     await processButtonclickImageRemoveYes(ctx,d)
        # if d.get("id") == str(INTER_ID_BUTTONCLICK_IMAGEREMOVENO):
        #     await processButtonclickImageRemoveNo(ctx,d)


@profile
async def processButtonclickImageView(ctx: discord.Interaction, thread_id: int):
    await ctx.response.send_message("画像を送信しています...", ephemeral=True)
    thread = client.get_channel(thread_id)

    # 元画像を取得
    async for m in thread.history(oldest_first=True, limit=1):
        files = [await a.to_file() for a in m.attachments]

    internal_id = await user_id_mapper.get_or_create_internal_id(ctx.user.id)

    # 既にキャッシュがあるかチェック
    async for m in thread.history(limit=None):
        if m.content == str(ctx.user.id):
            print("ALLOK - Using cached images")
            # キャッシュがある場合は既存の添付ファイルを再送信
            embed = discord.Embed(color=0x00DD00, title="画像を表示します")
            embed.add_field(name="画像数", value=f"{len(m.attachments)}枚")
            cached_files = [await a.to_file() for a in m.attachments]
            await ctx.edit_original_response(content=None, embed=embed, attachments=cached_files)
            return

    # キャッシュがない場合は暗号化して送信
    embed = discord.Embed(color=0x00DD00, title="画像を表示します")
    embed.add_field(name="読み込み中", value="暗号化処理中...")
    await ctx.edit_original_response(content=None, embed=embed)

    encrypted_files = []
    for i, file in enumerate(files):
        mycrypter = myCrypter(file2image(file))
        print(f"Encrypting image {i+1}/{len(files)}")
        mycrypter.setChannel([True, False, False, True]).encryptByID(internal_id).setChannel(
            [False, False, True, True]
        ).encryptByLabel(ctx.user.name).encryptByTime()
        encrypted_file = image2file(mycrypter.executeEncryption())
        encrypted_file.filename = file.filename
        encrypted_files.append(encrypted_file)

    # スレッドに保存
    msg: discord.Message = await thread.send(content=str(ctx.user.id), files=encrypted_files)

    # ユーザーに送信（Discordの仕様上、一度送信したFileオブジェクトは再利用不可のため再取得）
    embed = discord.Embed(color=0x00DD00, title="画像を表示します")
    embed.add_field(name="画像数", value=f"{len(encrypted_files)}枚")
    cached_files = [await a.to_file() for a in msg.attachments]
    await ctx.edit_original_response(content=None, embed=embed, attachments=cached_files)

    print(f"view id->{internal_id}")

    # メモリ解放
    del encrypted_files
    del cached_files
    gc.collect()


# @profile
async def processButtonclickImageRemove(ctx: discord.Interaction, prm: dict):
    if str(ctx.user.id) != prm.get("author_id"):
        embed = discord.Embed(colour=0xFF0000, title="Botエラー")
        embed.add_field(name="警告", value="この操作は投稿者にしか行えません。")
        await ctx.response.send_message(embed=embed, ephemeral=True)
    else:

        class YesButton(discord.ui.Button):
            def __init__(
                self,
                msg: discord.Message,
                style=discord.ButtonStyle.red,
                label="削除する",
            ):
                self.msg = msg
                super().__init__(style=style, label=label)

            async def callback(self, ctx: discord.Interaction):
                await self.msg.delete()
                for c in self.view.children:
                    c.disabled = True
                await ctx.response.edit_message(
                    content="削除しました。", view=self.view, delete_after=5
                )

        class NoButton(discord.ui.Button):
            def __init__(self, style=discord.ButtonStyle.gray, label="キャンセルする"):
                super().__init__(style=style, label=label)

            async def callback(self, ctx: discord.Interaction):
                for c in self.view.children:
                    c.disabled = True
                await ctx.response.edit_message(
                    content="キャンセルしました。", view=self.view, delete_after=5
                )

        # Yesbutton = discord.ui.Button(style=discord.ButtonStyle.red,label="削除する",custom_id=json.dumps({"id":str(INTER_ID_BUTTONCLICK_IMAGEREMOVEYES),"deletethreadid":prm.get("thread_id"),"deletemessageid":ctx.message.id}))
        # Nobutton = discord.ui.Button(style=discord.ButtonStyle.blurple,label="削除しない",custom_id=json.dumps({"id":str(INTER_ID_BUTTONCLICK_IMAGEREMOVENO)}))

        Yesbutton = YesButton(msg=ctx.message)
        Nobutton = NoButton()
        view = discord.ui.View(timeout=None)
        view.add_item(Yesbutton)
        view.add_item(Nobutton)
        await ctx.response.send_message(
            "本当に削除しますか？", view=view, ephemeral=True
        )


# @profile
@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.user):
    if reaction.message.flags.ephemeral:
        if reaction.emoji == EMOJI_BUTTON_PREVIOUS:
            pass


# @profile
@client.event
async def on_ready():
    global user_id_mapper
    print("ready")
    pool = await asyncpg.create_pool(DATABASE_URL)
    user_id_mapper = UserIdMapper(pool)
    await user_id_mapper.init()
    print("DB connected")
    await tree.sync()
    print("ready")


# @profile
def main():
    client.run(TOKEN)


if __name__ == "__main__":
    print("ready")
    main()

#######
