from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import textwrap
from myImageConcater import concateImage
import datetime


MASKBIT_ROW = 4
MASKBIT_COLUMN = 5
MASKBIT_LENGTH_NUM = 16
MASKBIT_LENGTH_CHECKSUM = 4

ID_MAX = 2**MASKBIT_LENGTH_NUM

MASK_BASE = 0
MASK_COLOR = 1
TEXT_COLOR = 64


class myCrypter:
    originalImageData: Image.Image
    maskImageData: Image.Image
    draw: ImageDraw.ImageDraw

    crypt_mode = [True, True, True, True]
    """RGBのチャンネルを管理
        0:R
        1:G
        2:B
        3:A
    """

    def __init__(self, im: Image.Image):
        self.originalImageData = im
        self.maskImageData = Image.new("RGBA", im.size, MASK_BASE)
        self.draw = ImageDraw.Draw(self.maskImageData)

    def setChannel(self, mode: list[bool]) -> myCrypter:
        self.crypt_mode = mode
        return self

    def _encrypt(self, im: Image.Image, im_mask: Image.Image) -> Image.Image:
        print("crypt")
        im_data = np.array(im)
        im_mask_data = np.array(im_mask)

        im_crypted_data = np.where(
            im_data < 128, im_data + im_mask_data, im_data - im_mask_data
        )

        im_crypted_data = im_crypted_data.astype("uint8")
        return Image.fromarray(im_crypted_data, mode="RGBA")

    def _decrypt(self, im_en: Image.Image, im_or: Image.Image) -> Image.Image:
        im_or_data = np.array(im_or)
        im_en_data = np.array(im_en)

        im_decrypted_data = abs(im_or_data - im_en_data).astype("uint8")
        return Image.fromarray(im_decrypted_data, mode="RGBA")

    def encryptByID(self, num: int) -> myCrypter:
        checker_width = int(self.maskImageData.width / MASKBIT_ROW)
        checker_height = int(self.maskImageData.height / MASKBIT_COLUMN)

        maskbooleanlist = self._num2bit(num, MASKBIT_LENGTH_NUM)
        maskbooleanlist = self.addChecksum(maskbooleanlist)

        for i in range(MASKBIT_COLUMN):
            for j in range(MASKBIT_ROW):
                if maskbooleanlist[i * MASKBIT_ROW + j]:
                    self.draw.rectangle(
                        (
                            checker_width * j,
                            checker_height * i,
                            checker_width * (j + 1),
                            checker_height * (i + 1),
                        ),
                        fill=(
                            MASK_COLOR * self.crypt_mode[0],
                            MASK_COLOR * self.crypt_mode[1],
                            MASK_COLOR * self.crypt_mode[2],
                            MASK_COLOR * self.crypt_mode[3],
                        ),
                    )
        return self

    def encryptByLabel(self, label: str) -> myCrypter:
        fontsize = int(min(self.maskImageData.width, self.maskImageData.height) / 15)
        fontfile = "./data/Arial Bold.ttf"

        wraplist = textwrap.wrap((label + " ") * 60, 25)
        fnt = ImageFont.truetype(fontfile, fontsize)

        for i, list in enumerate(wraplist):
            y = i * (fontsize * 1.5) + fontsize
            self.draw.text(
                (fontsize, y),
                list,
                fill=(
                    MASK_COLOR * self.crypt_mode[0],
                    MASK_COLOR * self.crypt_mode[1],
                    MASK_COLOR * self.crypt_mode[2],
                    MASK_COLOR * self.crypt_mode[3],
                ),
                font=fnt,
            )

        return self

    def encryptByTime(self) -> myCrypter:
        # text = "UMA"
        fontsize = int(min(self.maskImageData.width, self.maskImageData.height) / 30)
        fontfile = "./data/Arial Bold.ttf"
        fnt = ImageFont.truetype(fontfile, fontsize)
        t_delta = datetime.timedelta(hours=9)
        JST = datetime.timezone(t_delta, "JST")
        now = datetime.datetime.now(JST)
        text = now.strftime(r"%Y/%m/%d %H:%M:%S")
        w, h = self.draw.textbbox(xy=(0, 0), text=text, font=fnt)[2:]
        self.draw.text(
            (self.maskImageData.width - w, self.maskImageData.height - h),
            text,
            fill=(TEXT_COLOR, TEXT_COLOR, TEXT_COLOR, 0),
            font=fnt,
        )

        return self

    def executeEncryption(self) -> Image.Image:
        return self._encrypt(self.originalImageData, self.maskImageData)

    def decrypt(
        self, image_encrypted: Image.Image, image_original: Image.Image
    ) -> Image.Image:
        image_encrypted = image_encrypted.resize(
            image_original.size, resample=Image.Resampling.BILINEAR
        )

        image_encrypted = image_encrypted.convert("RGBA")

        image_original = image_original.convert("RGBA")

        image_decrypted = self._decrypt(image_encrypted, image_original)

        # print(image_decrypted.info)
        # image_decrypted.show()

        image_decrypted_data = np.array(image_decrypted)

        image_decrypted_data = (
            np.clip(image_decrypted_data, MASK_BASE, MASK_COLOR) * 255
        )

        # cmap = plt.get_cmap("viridis")
        # img = cmap(image_decrypted_data, bytes=True)
        # image_decrypted = Image.fromarray(img)

        # plt.imshow(image_decrypted_data)
        # plt.show()

        # print(image_decrypted_data)

        image_decrypted_r = Image.fromarray(image_decrypted_data[:, :, 0], mode="L")
        image_decrypted_g = Image.fromarray(image_decrypted_data[:, :, 1], mode="L")
        image_decrypted_b = Image.fromarray(image_decrypted_data[:, :, 2], mode="L")
        image_decrypted_a = Image.fromarray(image_decrypted_data[:, :, 3], mode="L")

        image_decrypted: Image.Image = Image.new(
            "RGBA", (image_original.width * 2, image_original.height * 3)
        )

        # image_decrypted.paste(image_decrypted_r,(0,0))
        # image_decrypted.paste(image_decrypted_g,(image_original.width,0))
        # image_decrypted.paste(image_decrypted_b,(0,image_original.height))
        # image_decrypted.paste(image_decrypted_a,(image_original.width,image_original.height))
        # image_decrypted.paste(Image.fromarray(image_decrypted_data[:,:,:3]),(0,image_original.height*2))
        # image_decrypted.paste(Image.fromarray(image_decrypted_data),(image_original.width,image_original.height*2))

        image_decrypted = concateImage(
            [
                [image_decrypted_r, image_decrypted_g],
                [image_decrypted_b, image_decrypted_a],
                [
                    Image.fromarray(image_decrypted_data[:, :, :3]),
                    Image.fromarray(image_decrypted_data),
                ],
            ]
        )

        # image_decrypted.show()

        # image_bit = np.zeros((MASKBIT_COLUMN,MASKBIT_ROW))

        # for i in range(MASKBIT_COLUMN):
        #     for j in range(MASKBIT_ROW):
        #         image_bit[i,j] = np.mean(image_decrypted_data[checker_height * i:checker_height*(i+1),checker_width * j:checker_width*(j+1)])

        # image_bit = image_bit.ravel()

        # model = KMeans(n_clusters=2,random_state=0,n_init='auto')

        # model.fit(image_bit.reshape(-1,1))

        # print(model.cluster_centers_)

        # list_bit_boolean = [b==np.argmax(model.cluster_centers_) for b in model.labels_]

        # id = checkChecksum(list_bit_boolean)

        return image_decrypted

    def _num2bit(self, num: int, padding: int) -> list[bool]:
        bitlist = format(num, f"0{padding}b")
        tmp = []
        for s in bitlist:
            if s == "0":
                tmp.append(False)
            else:
                tmp.append(True)
        return tmp

    def _bit2hum(self, list: list[bool]) -> int:
        tmp = 0
        for i, b in enumerate(reversed(list)):
            if b:
                tmp += 2**i
        return tmp

    def addChecksum(self, list: list[bool]):
        list += self._num2bit(sum(list), MASKBIT_LENGTH_CHECKSUM)
        return list

    def checkChecksum(self, list: list[bool]) -> int:
        bit = list[0:MASKBIT_LENGTH_NUM]
        checksum = self._bit2hum(list[MASKBIT_LENGTH_NUM:])
        if sum(bit) == checksum:
            return self._bit2hum(list[0:MASKBIT_LENGTH_NUM])
        else:
            return -1


if __name__ == "__main__":
    im = Image.open("./194-0021.png").convert("RGBA")
    ID = 372
    mycrypter = myCrypter(im)
    mycrypter.setChannel([True, False, False, True]).encryptByID(ID).setChannel(
        [False, True, False, True]
    ).encryptByLabel("testtest").setChannel([False, False, True, True]).encryptByTime()
    imcry = mycrypter.executeEncryption()
    imcry.save(f"encrypted{ID}.png")
    imdecry = mycrypter.decrypt(imcry, im)
    imdecry.save(f"decrypted{ID}.png")
