import pytest
import asyncio
import os
import tempfile
import json
from unittest.mock import patch, MagicMock, AsyncMock
from urllib.parse import urlparse

from app.tools.scraper_tool import (
    ScraperTool,
    ScraperToolError,
    InputValidationError,
    HttpError,
    TimeoutError,
    RateLimitError,
    SecurityError,
    ParsingError,
    RenderingError,
    ExternalToolError,
    HttpMethod,
    ContentType,
    OutputFormat,
    RenderEngine,
    ScraperSettings
)

# Fixtures
@pytest.fixture
def scraper_tool():
    """Create a ScraperTool instance for testing."""
    tool = ScraperTool({
        "timeout": 10,
        "user_agent": "TestUserAgent/1.0",
        "max_redirects": 3,
        "verify_ssl": False,
        "cache_ttl_seconds": 60,
        "cache_max_items": 10,
        "threadpool_workers": 2,
        "max_concurrent_requests": 5,
        "rate_limit_per_domain": {"example.com": 0.5},
        "default_rate_limit": 1.0,
        "allowed_domains": [],  # Empty means all domains allowed
        "blocked_domains": ["malicious.com"],
        "max_retries": 2
    })
    return tool

@pytest.fixture
def sample_html():
    """Create a sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <h1>Hello World</h1>
        <p class="content">This is a test paragraph.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
        <a href="https://example.com/page1">Link 1</a>
        <a href="https://example.com/page2">Link 2</a>
    </body>
    </html>
    """

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up after test
    import shutil
    shutil.rmtree(temp_dir)

# Basic functionality tests
@pytest.mark.asyncio
async def test_http_requests_get(scraper_tool):
    """Test HTTP GET request using requests."""
    with patch('app.tools.scraper_tool.requests.get') as mock_get:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "Test response content"
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = await scraper_tool.run('get', url='https://example.com')
        
        assert isinstance(result, dict)
        assert 'content' in result
        assert result['content'] == "Test response content"
        assert 'status_code' in result
        assert result['status_code'] == 200
        assert 'headers' in result
        
        # Verify the request was made with the correct parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == 'https://example.com'
        assert 'User-Agent' in kwargs['headers']
        assert kwargs['headers']['User-Agent'] == "TestUserAgent/1.0"
        assert kwargs['verify'] is False
        assert kwargs['timeout'] == 10

@pytest.mark.asyncio
async def test_http_requests_post(scraper_tool):
    """Test HTTP POST request using requests."""
    with patch('app.tools.scraper_tool.requests.post') as mock_post:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "Post response"
        mock_response.status_code = 201
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        result = await scraper_tool.run('post', 
                                       url='https://example.com/api', 
                                       data={"key": "value"},
                                       headers={"X-Custom-Header": "test"})
        
        assert isinstance(result, dict)
        assert 'content' in result
        assert result['content'] == "Post response"
        assert 'status_code' in result
        assert result['status_code'] == 201
        
        # Verify the request was made with the correct parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == 'https://example.com/api'
        assert 'User-Agent' in kwargs['headers']
        assert kwargs['headers']['X-Custom-Header'] == "test"
        assert kwargs['data'] == {"key": "value"}

@pytest.mark.asyncio
async def test_http_urllib(scraper_tool):
    """Test HTTP request using urllib."""
    with patch('app.tools.scraper_tool.urllib_request.Request') as mock_request:
        with patch('app.tools.scraper_tool.urllib_request.urlopen') as mock_urlopen:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.read.return_value = b"Test urllib response"
            mock_response.status = 200
            mock_response.headers = {"Content-Type": "text/plain"}
            mock_urlopen.return_value = mock_response
            
            result = await scraper_tool.run('get_urllib', url='https://example.com')
            
            assert isinstance(result, dict)
            assert 'content' in result
            assert result['content'] == "Test urllib response"
            assert 'status_code' in result
            assert result['status_code'] == 200
            
            # Verify the request was made with the correct parameters
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[0] == 'https://example.com'
            assert 'headers' in kwargs
            assert 'User-Agent' in kwargs['headers']

@pytest.mark.asyncio
async def test_http_aiohttp(scraper_tool):
    """Test HTTP request using aiohttp."""
    # Mock the ClientSession and response
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text.return_value = "Test aiohttp response"
    mock_session.__aenter__.return_value = mock_session
    mock_session.request.return_value.__aenter__.return_value = mock_response
    
    with patch('app.tools.scraper_tool.aiohttp.ClientSession', return_value=mock_session):
        result = await scraper_tool.run('get_aiohttp', url='https://example.com')
        
        assert isinstance(result, dict)
        assert 'content' in result
        assert result['content'] == "Test aiohttp response"
        assert 'status_code' in result
        assert result['status_code'] == 200
        
        # Verify the request was made with the correct parameters
        mock_session.request.assert_called_once()
        args, kwargs = mock_session.request.call_args
        assert kwargs['method'] == 'get'
        assert kwargs['url'] == 'https://example.com'
        assert 'headers' in kwargs
        assert 'User-Agent' in kwargs['headers']

@pytest.mark.asyncio
async def test_parse_html(scraper_tool, sample_html):
    """Test HTML parsing with BeautifulSoup."""
    result = await scraper_tool.run('parse_html', 
                                   html=sample_html, 
                                   selector='h1',
                                   selector_type='css',
                                   extract_text=True)
    
    assert isinstance(result, dict)
    assert 'matches' in result
    assert len(result['matches']) == 1
    assert result['matches'][0] == 'Hello World'
    
    # Test with different selector
    result = await scraper_tool.run('parse_html', 
                                   html=sample_html, 
                                   selector='li',
                                   selector_type='css',
                                   extract_text=True)
    
    assert isinstance(result, dict)
    assert 'matches' in result
    assert len(result['matches']) == 3
    assert 'Item 1' in result['matches']
    assert 'Item 2' in result['matches']
    assert 'Item 3' in result['matches']
    
    # Test with attribute extraction
    result = await scraper_tool.run('parse_html', 
                                   html=sample_html, 
                                   selector='a',
                                   selector_type='css',
                                   extract_attr='href',
                                   extract_text=False)
    
    assert isinstance(result, dict)
    assert 'matches' in result
    assert len(result['matches']) == 2
    assert 'https://example.com/page1' in result['matches']
    assert 'https://example.com/page2' in result['matches']

@pytest.mark.asyncio
async def test_render_page(scraper_tool):
    """Test JavaScript rendering with Playwright."""
    # Mock the Playwright functionality
    mock_sync_render = AsyncMock()
    mock_sync_render.return_value = {
        'html': '<html><body><h1>Rendered Content</h1></body></html>',
        'screenshot': None,
        'url': 'https://example.com',
        'title': 'Example Page'
    }
    
    with patch.object(scraper_tool, '_render_with_playwright', mock_sync_render):
        result = await scraper_tool.run('render', 
                                       url='https://example.com',
                                       engine=RenderEngine.PLAYWRIGHT,
                                       wait_time=2)
        
        assert isinstance(result, dict)
        assert 'html' in result
        assert 'Rendered Content' in result['html']
        assert 'url' in result
        assert 'title' in result
        
        # Verify the render was called with the correct parameters
        mock_sync_render.assert_called_once()
        args, kwargs = mock_sync_render.call_args
        assert args[0].url == 'https://example.com'
        assert args[0].wait_time == 2
        assert args[0].engine == RenderEngine.PLAYWRIGHT

@pytest.mark.asyncio
async def test_save_output(scraper_tool, temp_dir):
    """Test saving output to different formats."""
    content = {
        'title': 'Test Page',
        'content': 'This is test content',
        'items': ['item1', 'item2', 'item3']
    }
    
    # Test JSON output
    json_path = os.path.join(temp_dir, 'output.json')
    await scraper_tool._save_output(content, json_path, OutputFormat.JSON)
    
    assert os.path.exists(json_path)
    with open(json_path, 'r') as f:
        saved_content = json.load(f)
    assert saved_content['title'] == 'Test Page'
    assert saved_content['items'] == ['item1', 'item2', 'item3']
    
    # Test TEXT output
    text_path = os.path.join(temp_dir, 'output.txt')
    await scraper_tool._save_output(content, text_path, OutputFormat.TEXT)
    
    assert os.path.exists(text_path)
    with open(text_path, 'r') as f:
        saved_content = f.read()
    assert 'Test Page' in saved_content
    assert 'This is test content' in saved_content
    
    # Test HTML output
    html_path = os.path.join(temp_dir, 'output.html')
    await scraper_tool._save_output({'html': '<h1>Test HTML</h1>'}, html_path, OutputFormat.HTML)
    
    assert os.path.exists(html_path)
    with open(html_path, 'r') as f:
        saved_content = f.read()
    assert '<h1>Test HTML</h1>' in saved_content
    
    # Test MARKDOWN output
    md_path = os.path.join(temp_dir, 'output.md')
    await scraper_tool._save_output(content, md_path, OutputFormat.MARKDOWN)
    
    assert os.path.exists(md_path)
    with open(md_path, 'r') as f:
        saved_content = f.read()
    assert '# Scraper Results' in saved_content
    assert '## title' in saved_content
    assert 'Test Page' in saved_content

@pytest.mark.asyncio
async def test_crawl_scrapy(scraper_tool, temp_dir):
    """Test Scrapy crawling functionality."""
    # Mock subprocess.run
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = b"Scrapy crawl completed successfully"
    
    with patch('app.tools.scraper_tool.subprocess.run', return_value=mock_process):
        output_path = os.path.join(temp_dir, 'scrapy_output.json')
        
        # Create a dummy output file that Scrapy would have created
        with open(output_path, 'w') as f:
            json.dump([{"title": "Test Page", "url": "https://example.com"}], f)
        
        result = await scraper_tool.run('crawl_scrapy', 
                                       project_path='/path/to/scrapy/project',
                                       spider_name='test_spider',
                                       output_path=output_path,
                                       spider_args={'start_url': 'https://example.com'})
        
        assert isinstance(result, dict)
        assert 'success' in result
        assert result['success'] is True
        assert 'output_path' in result
        assert result['output_path'] == output_path
        assert 'items' in result
        assert len(result['items']) == 1
        assert result['items'][0]['title'] == 'Test Page'

# Error handling tests
@pytest.mark.asyncio
async def test_invalid_operation(scraper_tool):
    """Test handling of invalid operations."""
    with pytest.raises(InputValidationError):
        await scraper_tool.run('invalid_op', url='https://example.com')

@pytest.mark.asyncio
async def test_blocked_domain(scraper_tool):
    """Test handling of blocked domains."""
    with pytest.raises(SecurityError):
        await scraper_tool.run('get', url='https://malicious.com')

@pytest.mark.asyncio
async def test_http_error(scraper_tool):
    """Test handling of HTTP errors."""
    with patch('app.tools.scraper_tool.requests.get') as mock_get:
        # Setup mock response for 404 error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404 Client Error: Not Found")
        mock_get.return_value = mock_response
        
        with pytest.raises(HttpError):
            await scraper_tool.run('get', url='https://example.com/nonexistent')

@pytest.mark.asyncio
async def test_timeout_error(scraper_tool):
    """Test handling of timeout errors."""
    with patch('app.tools.scraper_tool.requests.get') as mock_get:
        # Setup mock response for timeout
        mock_get.side_effect = Exception("Connection timed out")
        
        with pytest.raises(Exception):  # Could be HttpError or TimeoutError depending on implementation
            await scraper_tool.run('get', url='https://example.com')

@pytest.mark.asyncio
async def test_rate_limiting(scraper_tool):
    """Test rate limiting functionality."""
    # Mock time.time to control the timing
    original_time = time.time
    mock_times = [100.0, 100.5, 101.0]  # First two requests are too close together
    
    with patch('app.tools.scraper_tool.time.time', side_effect=mock_times):
        with patch('app.tools.scraper_tool.asyncio.sleep') as mock_sleep:
            with patch('app.tools.scraper_tool.requests.get') as mock_get:
                # Setup mock response
                mock_response = MagicMock()
                mock_response.text = "Test response"
                mock_response.status_code = 200
                mock_response.headers = {}
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response
                
                # First request to example.com
                await scraper_tool.run('get', url='https://example.com')
                
                # Second request to example.com should be rate limited (0.5 req/sec)
                await scraper_tool.run('get', url='https://example.com')
                
                # Verify that sleep was called with the correct delay
                mock_sleep.assert_called_once()
                args, kwargs = mock_sleep.call_args
                assert args[0] > 0  # Should sleep for some positive amount of time

@pytest.mark.asyncio
async def test_cache_functionality(scraper_tool):
    """Test that caching works correctly."""
    with patch('app.tools.scraper_tool.requests.get') as mock_get:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "Test response content"
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # First call should not be cached
        result1 = await scraper_tool.run('get', url='https://example.com/cacheable')
        
        # Second call should use cache
        result2 = await scraper_tool.run('get', url='https://example.com/cacheable')
        
        # Verify get was called only once
        assert mock_get.call_count == 1
        assert result1 == result2

@pytest.mark.asyncio
async def test_parse_html_error(scraper_tool):
    """Test handling of HTML parsing errors."""
    with pytest.raises(ParsingError):
        await scraper_tool.run('parse_html', 
                              html="<invalid>html</unclosed>", 
                              selector='div',
                              selector_type='css')

@pytest.mark.asyncio
async def test_invalid_selector_type(scraper_tool, sample_html):
    """Test handling of invalid selector types."""
    with pytest.raises(InputValidationError):
        await scraper_tool.run('parse_html', 
                              html=sample_html, 
                              selector='div',
                              selector_type='invalid_selector_type')

@pytest.mark.asyncio
async def test_render_unavailable_engine(scraper_tool):
    """Test handling of unavailable rendering engines."""
    # Set playwright_available to False
    scraper_tool.settings.playwright_available = False
    scraper_tool.settings.selenium_available = False
    
    with pytest.raises(RenderingError):
        await scraper_tool.run('render', 
                              url='https://example.com',
                              engine=RenderEngine.PLAYWRIGHT)

@pytest.mark.asyncio
async def test_external_tool_error(scraper_tool):
    """Test handling of external tool errors."""
    # Mock subprocess.run to fail
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stdout = b"Scrapy crawl failed"
    mock_process.stderr = b"Error: Spider not found"
    
    with patch('app.tools.scraper_tool.subprocess.run', return_value=mock_process):
        with pytest.raises(ExternalToolError):
            await scraper_tool.run('crawl_scrapy', 
                                  project_path='/path/to/scrapy/project',
                                  spider_name='nonexistent_spider',
                                  output_path='/tmp/output.json')

@pytest.mark.asyncio
async def test_concurrency_limit(scraper_tool):
    """Test concurrency limiting."""
    # Set max_concurrent_requests to 1
    scraper_tool.settings.max_concurrent_requests = 1
    
    # Create a mock for _semaphore.acquire and release
    original_semaphore = scraper_tool._semaphore
    mock_acquire = AsyncMock()
    mock_release = AsyncMock()
    
    scraper_tool._semaphore.acquire = mock_acquire
    scraper_tool._semaphore.release = mock_release
    
    with patch('app.tools.scraper_tool.requests.get') as mock_get:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        await scraper_tool.run('get', url='https://example.com')
        
        # Verify semaphore was used
        mock_acquire.assert_called_once()
        mock_release.assert_called_once()
    
    # Restore original semaphore
    scraper_tool._semaphore = original_semaphore