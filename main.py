import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, timedelta
import threading
import schedule
import time

from scraper.scraper_manager import ScraperManager
from utils.email_sender import EmailSender
from config import CONFIG_FILE, DEFAULT_CONFIG

class RealEstateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Commercial Real Estate Crawler")
        self.root.geometry("900x700")
        
        # Initialize variables
        self.config = self.load_config()
        self.scraper_manager = ScraperManager()
        self.email_sender = EmailSender()
        
        # Set up theme
        self.use_dark_mode = tk.BooleanVar(value=self.config.get('dark_mode', True))
        self.setup_theme()
        
        self.setup_ui()
        self.apply_theme()
        
        # Setup scheduler if credentials are saved
        if self.config.get('save_credentials', False) and self.config.get('email', '') and self.config.get('email_password', ''):
            self.setup_scheduler()
        
        # Make the window responsive
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
    
    def load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Save current configuration to file"""
        # Update config with current UI values
        self.config.update({
            'property_types': [pt for pt, var in self.property_type_vars.items() if var.get()],
            'min_price': self.min_price_var.get(),
            'max_price': self.max_price_var.get(),
            'location': self.location_var.get(),
            'websites': [site for site, var in self.website_vars.items() if var.get()],
            'days_back': self.days_back_var.get(),
            'save_credentials': self.save_credentials_var.get(),
            'send_email': self.send_email_var.get(),
            'email': self.email_var.get(),
            'email_password': self.email_password_var.get() if self.save_credentials_var.get() else "",
            'dark_mode': self.use_dark_mode.get()
        })
        
        # Save to file
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)
    
    def setup_theme(self):
        """Configure the app's color theme"""
        self.light_theme = {
            'bg': '#f0f0f0', 'fg': '#333333', 'btn_bg': '#e0e0e0', 'btn_fg': '#333333',
            'highlight_bg': '#d0d0d0', 'input_bg': '#ffffff', 'accent': '#3498db'
        }
        
        self.dark_theme = {
            'bg': '#2d2d2d', 'fg': '#e0e0e0', 'btn_bg': '#444444', 'btn_fg': '#e0e0e0',
            'highlight_bg': '#505050', 'input_bg': '#3d3d3d', 'accent': '#3498db'
        }
        
        self.theme = self.dark_theme if self.use_dark_mode.get() else self.light_theme
    
    def apply_theme(self):
        """Apply the current theme to all widgets"""
        self.root.configure(bg=self.theme['bg'])
        for widget in self.root.winfo_children():
            if isinstance(widget, (tk.Frame, ttk.Frame)):
                widget.configure(bg=self.theme['bg'])
                for child in widget.winfo_children():
                    self.apply_theme_to_widget(child)
    
    def apply_theme_to_widget(self, widget):
        """Apply theme to a specific widget and its children"""
        if isinstance(widget, (tk.Label, tk.Checkbutton, tk.Radiobutton)):
            widget.configure(bg=self.theme['bg'], fg=self.theme['fg'])
        elif isinstance(widget, tk.Button):
            widget.configure(bg=self.theme['btn_bg'], fg=self.theme['btn_fg'], 
                           activebackground=self.theme['highlight_bg'])
        elif isinstance(widget, tk.Entry):
            widget.configure(bg=self.theme['input_bg'], fg=self.theme['fg'])
        elif isinstance(widget, tk.Frame):
            widget.configure(bg=self.theme['bg'])
            
        if hasattr(widget, 'winfo_children'):
            for child in widget.winfo_children():
                self.apply_theme_to_widget(child)
    
    def toggle_theme(self):
        """Switch between light and dark themes"""
        self.use_dark_mode.set(not self.use_dark_mode.get())
        self.theme = self.dark_theme if self.use_dark_mode.get() else self.light_theme
        self.apply_theme()
        self.save_config()
    
    def create_section_label(self, parent, text):
        """Create a section label with consistent styling"""
        tk.Label(parent, text=text, font=("Helvetica", 12, "bold"), 
               bg=self.theme['bg'], fg=self.theme['fg']).pack(anchor=tk.W, pady=(10, 5))
    
    def create_checkbox(self, parent, text, variable, padx=5, pady=2):
        """Create a themed checkbox"""
        tk.Checkbutton(parent, text=text, variable=variable,
                      bg=self.theme['bg'], fg=self.theme['fg'],
                      selectcolor=self.theme['highlight_bg']).pack(anchor=tk.W, padx=padx, pady=pady)
    
    def create_entry(self, parent, variable, width=25, show=None):
        """Create a themed entry field"""
        entry = tk.Entry(parent, textvariable=variable, width=width, show=show,
                        bg=self.theme['input_bg'], fg=self.theme['fg'])
        entry.pack(fill=tk.X, padx=5, pady=2)
        return entry
    
    def create_label(self, parent, text):
        """Create a themed label"""
        tk.Label(parent, text=text, bg=self.theme['bg'], fg=self.theme['fg']).pack(anchor=tk.W, padx=5, pady=2)
    
    def setup_ui(self):
        """Create the main UI elements"""
        # Create main frame with padding
        main_frame = tk.Frame(self.root, bg=self.theme['bg'], padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Make main frame responsive
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=0)  # Title row
        main_frame.rowconfigure(1, weight=1)  # Content row
        main_frame.rowconfigure(2, weight=0)  # Progress bar row
        
        # Title frame
        title_frame = tk.Frame(main_frame, bg=self.theme['bg'])
        title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        title_frame.columnconfigure(0, weight=1)
        
        tk.Label(title_frame, text="Commercial Real Estate Crawler", 
                font=("Helvetica", 16, "bold"), bg=self.theme['bg'], fg=self.theme['fg']).pack(side=tk.LEFT)
        
        tk.Button(title_frame, text="Toggle Theme", command=self.toggle_theme,
                 bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).pack(side=tk.RIGHT)
        
        # Create content frame to hold options and results
        content_frame = tk.Frame(main_frame, bg=self.theme['bg'])
        content_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=2)
        content_frame.rowconfigure(0, weight=1)
        
        # Create scrollable canvas for options panel
        options_canvas = tk.Canvas(content_frame, bg=self.theme['bg'], highlightthickness=0)
        options_canvas.grid(row=0, column=0, sticky="nsew")
        
        options_scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=options_canvas.yview)
        options_scrollbar.grid(row=0, column=0, sticky="nse")
        
        options_canvas.configure(yscrollcommand=options_scrollbar.set)
        
        # Create left panel for search options
        options_frame = tk.Frame(options_canvas, bg=self.theme['bg'], padx=10, pady=10)
        options_canvas.create_window((0, 0), window=options_frame, anchor="nw")
        
        # Property Types
        self.create_section_label(options_frame, "Property Types")
        property_types_frame = tk.Frame(options_frame, bg=self.theme['bg'])
        property_types_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.property_type_vars = {}
        # Reordered property types to match commercialmls_scraper.py order
        property_types = ['MultiFamily', 'Industrial', 'Office', 'Retail']
        for i, prop_type in enumerate(property_types):
            var = tk.BooleanVar(value=prop_type in self.config.get('property_types', []))
            self.property_type_vars[prop_type] = var
            self.create_checkbox(property_types_frame, prop_type, var)
        
        # Price Range
        self.create_section_label(options_frame, "Price Range")
        price_frame = tk.Frame(options_frame, bg=self.theme['bg'])
        price_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.min_price_var = tk.StringVar(value=self.config.get('min_price', ''))
        self.max_price_var = tk.StringVar(value=self.config.get('max_price', ''))
        
        self.create_label(price_frame, "Min ($):")
        self.create_entry(price_frame, self.min_price_var, width=15)
        
        self.create_label(price_frame, "Max ($):")
        self.create_entry(price_frame, self.max_price_var, width=15)
        
        # Location
        self.create_section_label(options_frame, "Location")
        location_frame = tk.Frame(options_frame, bg=self.theme['bg'])
        location_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.location_var = tk.StringVar(value=self.config.get('location', 'Seattle, WA'))
        self.create_entry(location_frame, self.location_var)
        
        # Websites
        self.create_section_label(options_frame, "Websites")
        websites_frame = tk.Frame(options_frame, bg=self.theme['bg'])
        websites_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.website_vars = {}
        websites = ['commercialmls.com', 'loopnet.com']
        for website in websites:
            var = tk.BooleanVar(value=website in self.config.get('websites', []))
            self.website_vars[website] = var
            self.create_checkbox(websites_frame, website, var)
        
        # Date Range
        self.create_section_label(options_frame, "Date Range")
        date_frame = tk.Frame(options_frame, bg=self.theme['bg'])
        date_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.days_back_var = tk.IntVar(value=self.config.get('days_back', 1))
        tk.Spinbox(date_frame, from_=1, to=30, textvariable=self.days_back_var, width=5, 
                 bg=self.theme['input_bg'], fg=self.theme['fg']).pack(side=tk.LEFT, padx=5)
        
        # Email Options
        self.create_section_label(options_frame, "Email Options")
        email_frame = tk.Frame(options_frame, bg=self.theme['bg'])
        email_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.send_email_var = tk.BooleanVar(value=self.config.get('send_email', False))
        self.save_credentials_var = tk.BooleanVar(value=self.config.get('save_credentials', False))
        
        self.create_checkbox(email_frame, "Send Results by Email", self.send_email_var)
        self.create_checkbox(email_frame, "Save Email Credentials", self.save_credentials_var)
        
        self.create_label(email_frame, "Email:")
        self.email_var = tk.StringVar(value=self.config.get('email', ''))
        self.create_entry(email_frame, self.email_var)
        
        self.create_label(email_frame, "Password:")
        self.email_password_var = tk.StringVar(value=self.config.get('email_password', ''))
        self.create_entry(email_frame, self.email_password_var, show="*")
        
        # Search Button
        tk.Button(options_frame, text="Search Now", command=self.search_listings,
                 bg=self.theme['accent'], fg="#ffffff", font=("Helvetica", 12, "bold"),
                 padx=20, pady=10).pack(pady=15, fill=tk.X)
        
        # Update scroll region when options frame changes size
        options_frame.update_idletasks()
        options_canvas.config(scrollregion=options_canvas.bbox("all"))
        
        # Bind mousewheel to scroll options
        def _on_mousewheel(event):
            options_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        options_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Results panel
        self.setup_results_panel(content_frame)
        
        # Progress bars
        progress_frame = tk.Frame(main_frame, bg=self.theme['bg'], padx=10, pady=10)
        progress_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.setup_progress_bars(progress_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W,
                bg=self.theme['highlight_bg'], fg=self.theme['fg']).pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_progress_bars(self, parent):
        """Set up progress bars for each website"""
        # Make the progress frame use all available width
        parent.columnconfigure(1, weight=1)
        
        # LoopNet progress
        tk.Label(parent, text="LoopNet:", bg=self.theme['bg'], fg=self.theme['fg']).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.loopnet_progress = ttk.Progressbar(parent, mode='determinate')
        self.loopnet_progress.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.loopnet_status = tk.Label(parent, text="LoopNet: 0%", width=15, bg=self.theme['bg'], fg=self.theme['fg'])
        self.loopnet_status.grid(row=0, column=2, padx=5, pady=2)
        
        # CommercialMLS progress
        tk.Label(parent, text="CommercialMLS:", bg=self.theme['bg'], fg=self.theme['fg']).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.commercialmls_progress = ttk.Progressbar(parent, mode='determinate')
        self.commercialmls_progress.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.commercialmls_status = tk.Label(parent, text="CommercialMLS: 0%", width=15, bg=self.theme['bg'], fg=self.theme['fg'])
        self.commercialmls_status.grid(row=1, column=2, padx=5, pady=2)
    
    def setup_results_panel(self, parent):
        """Set up the results display panel"""
        results_frame = tk.Frame(parent, bg=self.theme['bg'], padx=10, pady=10)
        results_frame.grid(row=0, column=1, sticky="nsew")
        results_frame.rowconfigure(1, weight=1)
        results_frame.columnconfigure(0, weight=1)
        
        tk.Label(results_frame, text="Search Results", font=("Helvetica", 14, "bold"), 
               bg=self.theme['bg'], fg=self.theme['fg']).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        results_container = tk.Frame(results_frame, bg=self.theme['bg'])
        results_container.grid(row=1, column=0, sticky="nsew")
        results_container.rowconfigure(0, weight=1)
        results_container.columnconfigure(0, weight=1)
        
        scrollbar = tk.Scrollbar(results_container)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.results_text = tk.Text(results_container, wrap=tk.WORD,
                                  bg=self.theme['input_bg'], fg=self.theme['fg'],
                                  yscrollcommand=scrollbar.set)
        self.results_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.results_text.yview)
        
        # Bind window resize events to update canvas scrollregion
        def on_configure(event):
            parent.update_idletasks()
            for widget in self.root.winfo_children():
                widget.update_idletasks()
        
        self.root.bind("<Configure>", on_configure)
    
    def format_listing(self, listing):
        """Format a single listing for display"""
        text = f"Address: {listing.get('address', 'No address')}\n"
        text += f"Price: {listing.get('price', 'Price not available')}\n"
        text += f"Type: {listing.get('property_type', 'Not specified')}\n"
        
        if 'location' in listing:
            text += f"Location: {listing['location']}\n"
            
        if 'date_listed' in listing:
            text += f"Date Listed: {listing['date_listed']}\n"
            
        text += f"URL: {listing.get('url', 'No URL available')}\n\n"
        return text
    
    def display_results(self, results):
        """Display search results in the UI"""
        self.root.after(0, lambda: self.results_text.delete(1.0, tk.END))
        
        if not results:
            self.root.after(0, lambda: self.results_text.insert(tk.END, "No results found matching your criteria."))
            return
        
        # Check if results is a dict (multiple sites) or list (single site)
        if isinstance(results, dict):
            total_count = sum(len(site_results) for site_results in results.values())
            self.root.after(0, lambda: self.results_text.insert(tk.END, f"Found {total_count} listings:\n\n"))
            
            for website, listings in results.items():
                if listings:
                    self.root.after(0, lambda w=website: self.results_text.insert(tk.END, f"--- {w.upper()} ---\n\n"))
                    for listing in listings:
                        self.root.after(0, lambda l=listing: self.results_text.insert(tk.END, self.format_listing(l)))
        else:
            self.root.after(0, lambda: self.results_text.insert(tk.END, f"Found {len(results)} listings:\n\n"))
            for listing in results:
                self.root.after(0, lambda l=listing: self.results_text.insert(tk.END, self.format_listing(l)))
    
    def update_progress(self, website, progress):
        """Update progress bar for a specific website"""
        if website == 'loopnet':
            self.loopnet_progress['value'] = progress * 100
            self.loopnet_status['text'] = f"LoopNet: {int(progress * 100)}%"
        elif website == 'commercialmls':
            self.commercialmls_progress['value'] = progress * 100
            self.commercialmls_status['text'] = f"CommercialMLS: {int(progress * 100)}%"
    
    def search_listings(self):
        """Execute the search based on current parameters"""
        if not any(var.get() for var in self.property_type_vars.values()):
            messagebox.showerror("Error", "Please select at least one property type")
            return
            
        if not any(var.get() for var in self.website_vars.values()):
            messagebox.showerror("Error", "Please select at least one website")
            return
        
        self.save_config()
        self.status_var.set("Searching...")
        
        # Reset progress bars
        self.loopnet_progress['value'] = 0
        self.commercialmls_progress['value'] = 0
        self.loopnet_status['text'] = "LoopNet: 0%"
        self.commercialmls_status['text'] = "CommercialMLS: 0%"
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Searching for listings...\n\n")
        self.root.update()
        
        search_params = {
            'property_types': [pt for pt, var in self.property_type_vars.items() if var.get()],
            'min_price': self.min_price_var.get(),
            'max_price': self.max_price_var.get(),
            'location': self.location_var.get(),
            'websites': [site for site, var in self.website_vars.items() if var.get()],
            'days_back': self.days_back_var.get()
        }
        
        threading.Thread(target=self.execute_search, args=(search_params,), daemon=True).start()
    
    def execute_search(self, search_params):
        """Execute the search in a background thread"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=search_params['days_back'])

            # Set up progress callbacks
            progress_callbacks = {
                website: lambda p, w=website: self.root.after(0, lambda p=p, w=w: self.update_progress(w, p))
                for website in [site.split('.')[0].lower() for site in search_params['websites']]
            }
            
            # Create a new scraper manager with debug mode enabled
            scraper_manager = ScraperManager(debug_mode=False)
            
            # Execute search
            results = scraper_manager.search(
                property_types=search_params['property_types'],
                location=search_params['location'],
                min_price=search_params['min_price'],
                max_price=search_params['max_price'],
                start_date=start_date,
                end_date=end_date,
                websites=search_params['websites'],
                progress_callbacks=progress_callbacks
            )
            
            # Display results
            self.display_results(results)
            
            # Send email if requested
            if self.send_email_var.get() and self.email_var.get():
                self.send_email_results(results)
                
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            self.results_text.insert(tk.END, f"\nError occurred: {str(e)}")
            import traceback
            self.results_text.insert(tk.END, f"\n{traceback.format_exc()}")
        finally:
            self.root.after(0, lambda: self.status_var.set("Ready"))
    
    def send_email_results(self, results):
        """Send results via email"""
        if not self.email_var.get():
            return
            
        try:
            subject = f"Commercial Real Estate Listings - {datetime.now().strftime('%Y-%m-%d')}"
            body = "Commercial Real Estate Listings\n\n"
            
            if isinstance(results, dict):
                total_count = sum(len(site_results) for site_results in results.values())
                body += f"Found {total_count} listings:\n\n"
                
                for website, listings in results.items():
                    if listings:
                        body += f"--- {website.upper()} ---\n\n"
                        for listing in listings:
                            body += self.format_listing(listing)
            else:
                body += f"Found {len(results)} listings:\n\n"
                for listing in results:
                    body += self.format_listing(listing)
            
            self.email_sender.send_email(
                to_email=self.email_var.get(),
                subject=subject,
                body=body,
                email=self.email_var.get(),
                password=self.email_password_var.get()
            )
            
            self.root.after(0, lambda: self.results_text.insert(tk.END, "\nResults sent via email."))
            
        except Exception as e:
            self.root.after(0, lambda: self.results_text.insert(tk.END, f"\nError sending email: {str(e)}"))
    
    def setup_scheduler(self):
        """Set up the daily scheduler for automated searches"""
        schedule.every().day.at("09:00").do(self.run_scheduled_search)
        threading.Thread(target=self.scheduler_loop, daemon=True).start()
    
    def scheduler_loop(self):
        """Run the scheduler loop in background"""
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def run_scheduled_search(self):
        """Run automated search and email results"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            search_params = {
                'property_types': self.config.get('property_types', []),
                'min_price': self.config.get('min_price', ''),
                'max_price': self.config.get('max_price', ''),
                'location': self.config.get('location', 'Seattle, WA'),
                'websites': self.config.get('websites', []),
                'start_date': start_date,
                'end_date': end_date
            }
            
            results = self.scraper_manager.search(**search_params)
            
            if results and self.config.get('email', ''):
                subject = f"Daily Commercial Real Estate Listings - {datetime.now().strftime('%Y-%m-%d')}"
                body = "Daily Commercial Real Estate Listings\n\n"
                
                if isinstance(results, dict):
                    total_count = sum(len(site_results) for site_results in results.values())
                    body += f"Found {total_count} new listings in the last 24 hours:\n\n"
                    
                    for website, listings in results.items():
                        if listings:
                            body += f"--- {website.upper()} ---\n\n"
                            for listing in listings:
                                body += self.format_listing(listing)
                else:
                    body += f"Found {len(results)} new listings in the last 24 hours:\n\n"
                    for listing in results:
                        body += self.format_listing(listing)
                
                self.email_sender.send_email(
                    to_email=self.config.get('email', ''),
                    subject=subject,
                    body=body,
                    email=self.config.get('email', ''),
                    password=self.config.get('email_password', '')
                )
        except Exception as e:
            print(f"Error in scheduled search: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RealEstateApp(root)
    root.mainloop() 