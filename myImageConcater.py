from PIL import Image

def concateImage(images:list[list[Image.Image]]):
    column = len(images)
    row = max([len(i) for i in images])
    height = max([max(i1,key = lambda i:i.height).height for i1 in images])
    width = max([max(i1,key = lambda i:i.width).width for i1 in images])
    image_concated:Image.Image = Image.new("RGBA",(width * row,height * column))
    for i in range(column):
        for j in range(row):
            image_concated.paste(images[i][j],(width*j,height*i))
    return image_concated


if __name__ == "__main__":
    im1 = Image.open("./GAyh_0obgAAeNLR.jpeg").convert("RGBA")
    im2 = Image.open("./gabigabi.jpg").convert("RGBA")
    im3 = Image.open("./g0161.jpg").convert("RGBA")
    im4 = Image.open("./homo3651.png").convert("RGBA")
    concateImage([[im1,im2],
                  [im3,im4]]).show()