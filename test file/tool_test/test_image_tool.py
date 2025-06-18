import os
import pytest
import tempfile
import shutil
import asyncio
from PIL import Image
from app.tools.image_tool import ImageTool

# 创建测试用的图像文件
@pytest.fixture
def test_image():
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    # 创建测试图像
    img_path = os.path.join(temp_dir, "test.jpg")
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path)

    # 创建带文本的测试图像
    text_img_path = os.path.join(temp_dir, "text_image.png")
    text_img = Image.new('RGB', (200, 100), color='white')
    text_img.save(text_img_path)

    yield {"dir": temp_dir, "image": img_path, "text_image": text_img_path}

    # 测试后清理
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_load(test_image):
    """测试加载图像功能"""
    tool = ImageTool()
    result = await tool.run(op='load', file_path=test_image["image"])
    assert isinstance(result, dict)
    assert 'size' in result
    assert result['size'] == (100, 100)
    assert 'mode' in result
    assert result['mode'] == 'RGB'

@pytest.mark.asyncio
async def test_metadata(test_image):
    """测试获取图像元数据功能"""
    tool = ImageTool()
    result = await tool.run(op='metadata', file_path=test_image["image"], include_exif=True)
    assert isinstance(result, dict)
    assert 'size' in result
    assert 'mode' in result
    assert 'exif' in result

@pytest.mark.asyncio
async def test_resize(test_image):
    """测试调整图像大小功能"""
    tool = ImageTool()
    output_path = os.path.join(test_image["dir"], "resized.jpg")
    result = await tool.run(op='resize', file_path=test_image["image"],
                           output_path=output_path, width=50, height=50)
    assert result['success']
    assert os.path.isfile(output_path)
    # 验证调整大小是否正确
    with Image.open(output_path) as img:
        assert img.size == (50, 50)

@pytest.mark.asyncio
async def test_filter(test_image):
    """测试应用滤镜功能"""
    tool = ImageTool()
    output_path = os.path.join(test_image["dir"], "filtered.jpg")
    result = await tool.run(op='filter', file_path=test_image["image"],
                           output_path=output_path, filter_type='blur')
    assert result['success']
    assert os.path.isfile(output_path)


@pytest.mark.asyncio
async def test_metrics_collection():
    """测试性能指标收集功能"""
    tool = ImageTool()
    # 创建临时测试图像
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(temp_file.name)
        temp_path = temp_file.name

    try:
        # 执行几次操作以生成指标
        for _ in range(3):
            await tool.run(op='load', file_path=temp_path)

        # 获取指标
        metrics = tool.get_metrics()
        assert 'load' in metrics
        assert metrics['load']['total_calls'] >= 3
        assert metrics['load']['avg_time'] > 0
        assert metrics['load']['cache_hit_rate'] > 0  # 应该有一些缓存命中
    finally:
        os.unlink(temp_path)

@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理功能"""
    tool = ImageTool()
    with pytest.raises(Exception):
        await tool.run(op='load', file_path='nonexistent.jpg')

@pytest.mark.asyncio
async def test_invalid_filter_type(test_image):
    """测试无效滤镜类型的处理"""
    tool = ImageTool()
    output_path = os.path.join(test_image["dir"], "invalid_filter.jpg")
    with pytest.raises(Exception):
        await tool.run(op='filter', file_path=test_image["image"],
                      output_path=output_path, filter_type='invalid_filter')

# 测试OCR功能 - 注意这个测试可能会被跳过，如果系统上没有安装Tesseract
@pytest.mark.asyncio
async def test_ocr(test_image):
    """测试OCR功能，如果可用"""
    tool = ImageTool()
    try:
        result = await tool.run(op='ocr', file_path=test_image["text_image"], lang='eng')
        assert isinstance(result, str)
    except Exception as e:
        if "No Tesseract processes available" in str(e):
            pytest.skip("Tesseract not available, skipping OCR test")
        else:
            raise
