use anyhow::Result;
use winit::{
    application::ApplicationHandler,
    event::WindowEvent,
    event_loop::{ActiveEventLoop, EventLoop},
    window::{Window, WindowId},
};
use wry::WebViewBuilder;

struct App {
    html: String,
    window: Option<Window>,
    _webview: Option<wry::WebView>,
}

impl ApplicationHandler for App {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        let window = event_loop
            .create_window(Window::default_attributes().with_title("qernel viewer"))
            .expect("create_window");

        let webview = WebViewBuilder::new()
            .with_html(self.html.clone())
            .build(&window)
            .expect("build webview");

        self.window = Some(window);
        self._webview = Some(webview);
    }

    fn window_event(&mut self, event_loop: &ActiveEventLoop, _: WindowId, event: WindowEvent) {
        if let WindowEvent::CloseRequested = event {
            event_loop.exit();
        }
    }
}

/// Open a small native window that renders the provided HTML string.
/// Currently supports macOS via system WebView. Other platforms may require extra deps.
pub fn open_html(html: &str) -> Result<()> {
    let event_loop = EventLoop::new()?;
    let mut app = App { html: html.to_string(), window: None, _webview: None };
    event_loop.run_app(&mut app)?;
    Ok(())
}

struct AppUrl {
    url: String,
    window: Option<Window>,
    _webview: Option<wry::WebView>,
}

impl ApplicationHandler for AppUrl {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        let window = event_loop
            .create_window(Window::default_attributes().with_title("qernel viewer"))
            .expect("create_window");

        let webview = WebViewBuilder::new()
            .with_url(&self.url)
            .build(&window)
            .expect("build webview");

        self.window = Some(window);
        self._webview = Some(webview);
    }

    fn window_event(&mut self, event_loop: &ActiveEventLoop, _: WindowId, event: WindowEvent) {
        if let WindowEvent::CloseRequested = event {
            event_loop.exit();
        }
    }
}

/// Open a small native window and navigate to a URL.
/// macOS uses WebKit. On Linux/Windows, platform prerequisites apply.
pub fn open_url(url: &str) -> Result<()> {
    let event_loop = EventLoop::new()?;
    let mut app = AppUrl { url: url.to_string(), window: None, _webview: None };
    event_loop.run_app(&mut app)?;
    Ok(())
}


