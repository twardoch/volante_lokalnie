#!/usr/bin/env python3
# this_file: src/volante_lokalnie/tui.py

"""Textual TUI for Volante Lokalnie."""

from pathlib import Path
from typing import cast

import platformdirs
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll, Grid
from textual.screen import Screen
from textual.validation import Function
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    DataTable,
    Markdown,
    MarkdownViewer,
    TextArea,
    LoadingIndicator,
    ProgressBar,
    Static,
)
from textual.worker import Worker, get_current_worker
from textual_fspicker import FileOpen

from volante_lokalnie.volante_lokalnie import (
    OfferData,
    OfferDatabase,
    ScrapeExecutor,
    VolanteCLI,
)

# Use the same database path as the CLI
DB_FILE = Path(platformdirs.user_desktop_path()) / "volante_lokalnie.toml"


class StatsPanel(Static):
    """Panel showing offer statistics."""

    def compose(self) -> ComposeResult:
        """Compose the stats panel."""
        # Stats grid
        with Horizontal(id="stats-grid"):
            with Static(classes="stat-item"):
                yield Label("Total Offers:", classes="stat-label")
                yield Label("0", id="total-offers", classes="stat-value")
            with Static(classes="stat-item"):
                yield Label("Total Value:", classes="stat-label")
                yield Label("0.00 zł", id="total-value", classes="stat-value")
            with Static(classes="stat-item"):
                yield Label("Total Views:", classes="stat-label")
                yield Label("0", id="total-views", classes="stat-value")
            with Static(classes="stat-item"):
                yield Label("Pending:", classes="stat-label")
                yield Label("0", id="pending-changes", classes="stat-value")

    def update_stats(self, offers: dict) -> None:
        """Update the statistics display.

        Args:
            offers: Dictionary of offers to calculate stats from
        """
        total_offers = len(offers)
        total_value = sum(offer.price for offer in offers.values())
        total_views = sum(offer.views for offer in offers.values())
        pending_changes = sum(
            1
            for offer in offers.values()
            if not offer.published and (offer.title_new or offer.desc_new)
        )

        self.query_one("#total-offers", Label).update(str(total_offers))
        self.query_one("#total-value", Label).update(f"{total_value:.2f} zł")
        self.query_one("#total-views", Label).update(str(total_views))
        self.query_one("#pending-changes", Label).update(str(pending_changes))


class OfferDetailsScreen(Screen):
    """Screen to display offer details and allow editing."""

    BINDINGS = [
        ("b", "app.pop_screen", "Back"),
        ("escape", "app.pop_screen", "Back"),
        ("r", "refresh_offer", "Refresh Offer"),
        ("p", "publish_offer", "Publish Offer"),
    ]

    def __init__(
        self,
        offer_data: OfferData,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the offer details screen.

        Args:
            offer_data: The offer data to display
            name: Optional screen name
            id: Optional screen ID
            classes: Optional CSS classes
        """
        super().__init__(name, id, classes)
        self.offer_data = offer_data
        self.offer_id = offer_data.offer_id

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()

        with Grid(id="details-grid"):
            # Left column - Current values
            with Container(classes="details-column"):
                yield Label("Current Title:")
                yield Input(value=self.offer_data.title, disabled=True)
                yield Label("Current Description:")
                yield MarkdownViewer(
                    self.offer_data.desc or "*No description available.*",
                    show_table_of_contents=False,
                    id="detail-desc-current",
                )

            # Right column - New values
            with Container(classes="details-column"):
                yield Label("New Title:")
                yield Input(
                    value=self.offer_data.title_new,
                    placeholder="Enter new title",
                    id="detail-title-new",
                )
                yield Label("New Description:")
                yield TextArea(
                    self.offer_data.desc_new or "",
                    id="detail-desc-new",
                    show_line_numbers=False,
                )

        yield Footer()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "detail-title-new":
            self.action_save_offer()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle textarea changes."""
        if event.text_area.id == "detail-desc-new":
            self.action_save_offer()

    def on_focus_out(self, event) -> None:
        """Handle focus out events."""
        if isinstance(event.control, (Input, TextArea)):
            self.action_save_offer()

    def action_refresh_offer(self) -> None:
        """Handle refresh action."""
        cast(VolanteTUI, self.app).executor.execute_read(self.offer_id)
        # Refresh the screen data
        self.offer_data = cast(VolanteTUI, self.app).db.get_offer(self.offer_id)
        self.app.notify("Offer refreshed!")

    def action_save_offer(self) -> None:
        """Handle save action."""
        new_title = self.query_one("#detail-title-new", Input).value
        new_desc = self.query_one("#detail-desc-new", TextArea).text

        # Update both title and description
        if new_title != self.offer_data.title_new:
            self.app.cli.set_title(self.offer_id, new_title)
        if new_desc != self.offer_data.desc_new:
            self.app.cli.set_desc(self.offer_id, new_desc)

        # Refresh data
        self.offer_data = cast(VolanteTUI, self.app).db.get_offer(self.offer_id)
        self.app.notify("Changes saved locally")

    def action_publish_offer(self) -> None:
        """Handle publish action."""
        cast(VolanteTUI, self.app).executor.execute_publish(self.offer_id)
        self.offer_data = cast(VolanteTUI, self.app).db.get_offer(self.offer_id)
        self.app.notify("Changes published!")


class MainScreen(Screen):
    """Main screen with offer list and actions."""

    # Base bindings (always shown)
    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("o", "open_database", "Open Database"),
        ("r", "refresh_offers", "Refresh All"),
        ("s", "sort_offers", "Sort"),
        ("1", "sort_by_title", "Sort by Title"),
        ("2", "sort_by_price", "Sort by Price"),
        ("3", "sort_by_views", "Sort by Views"),
        ("4", "sort_by_status", "Sort by Status"),
    ]

    # Additional bindings when viewing list
    LIST_BINDINGS = [
        ("p", "publish_all", "Publish All"),
        ("enter", "view_details", "View Details"),
    ]

    # Additional bindings when viewing details
    DETAILS_BINDINGS = [
        ("escape,b", "back", "Back"),
        ("r", "refresh_offer", "Refresh Offer"),
        ("s,enter", "save_offer", "Save"),
        ("p", "publish_offer", "Publish Offer"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.current_offer: OfferData | None = None

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        yield Label(str(DB_FILE), id="db-path")
        yield ProgressBar(id="progress", total=100)

        # Main content area
        with Horizontal(id="main-content"):
            # Left side: Stats panel and offer table
            with Container(id="offer-list-container"):
                yield StatsPanel(id="stats-panel")
                table = DataTable(id="offer-table", fixed_rows=1)  # Keep header visible
                table.cursor_type = "row"
                table.zebra_stripes = True
                table.add_columns("Title", "Price", "Views", "Status")
                yield table
                yield LoadingIndicator(id="loading")

            # Right side: Details view (hidden by default)
            with Container(id="details-container"):
                with VerticalScroll(id="details-scroll"):
                    yield Static(
                        "Select an offer to view details", id="details-placeholder"
                    )

        # Add footer to show bindings
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        # Hide loading indicators initially
        self.query_one("#loading").display = False
        self._toggle_progress(False)
        # Refresh the offers list with current data
        self.refresh_offers_list()

    def _toggle_progress(self, show: bool = True) -> None:
        """Toggle between showing progress bar or database path."""
        progress = self.query_one("#progress")
        db_path = self.query_one("#db-path")
        progress.display = show
        db_path.display = not show

    def action_open_database(self) -> None:
        """Open a file picker to select a database file."""

        def handle_selected(path: str) -> None:
            if path:
                self._open_database(path)

        picker = FileOpen(
            "Select Database File",
            "Select a TOML database file to open",
            filters=[".toml"],
        )
        self.app.push_screen(picker, callback=handle_selected)

    def _open_database(self, path: str) -> None:
        """Open a database file.

        Args:
            path: Path to the database file
        """
        try:
            db_path = Path(path)
            if not db_path.exists():
                # Create parent directories if they don't exist
                db_path.parent.mkdir(parents=True, exist_ok=True)
                # Create an empty database file
                self.app.db = OfferDatabase(db_path)
                self.app.db.save()
            else:
                # Load existing database
                self.app.db = OfferDatabase(db_path)
                self.app.db.load()

            self.query_one("#db-path", Label).update(str(db_path))
            self.refresh_offers_list()
            self.app.notify(f"Opened database: {db_path}")
        except Exception as e:
            self.app.notify(f"Error opening database: {e}", severity="error")

    def refresh_offers_list(self) -> None:
        """Refreshes the list of offers."""
        table = self.query_one("#offer-table", DataTable)
        stats_panel = self.query_one("#stats-panel", StatsPanel)

        table.clear()  # Clear existing rows
        for offer_url, offer_data in cast(
            VolanteTUI, self.app
        ).db._get_items_by_date_asc():
            status = (
                "⚠ Pending"
                if not offer_data.published
                and (offer_data.title_new or offer_data.desc_new)
                else ""
            )
            table.add_row(
                offer_data.title,
                f"{offer_data.price:.2f} zł",
                str(offer_data.views),
                status,
                key=offer_data.offer_id,
            )

        # Update stats
        stats_panel.update_stats(cast(VolanteTUI, self.app).db.data)
        # Show database path
        self._toggle_progress(False)

    @on(Button.Pressed, "#refresh-btn")
    def handle_refresh(self) -> None:
        """Handle refresh button press."""
        self.action_refresh_offers()

    @on(Button.Pressed, "#publish-btn")
    def handle_publish(self) -> None:
        """Handle publish button press."""
        self.action_publish_all()

    @on(Button.Pressed, "#finish-btn")
    def handle_finish(self) -> None:
        """Handle finish button press."""
        self.app.exit()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the data table."""
        offer_id = event.row_key
        offer_data = cast(VolanteTUI, self.app).db.get_offer(offer_id)
        self.current_offer = offer_data
        self.show_details(offer_data)
        # Focus the new title input
        self.query_one("#detail-title-new").focus()

    def show_details(self, offer_data: OfferData) -> None:
        """Show offer details in the right panel."""
        details = self.query_one("#details-container")

        # First remove all existing content and widgets
        details.remove_children()
        details.add_class("visible")
        self.current_offer = offer_data

        # Create a vertical scroll container for the content
        scroll = VerticalScroll()
        details.mount(scroll)

        # Create the details grid
        grid = Grid(id="details-grid")
        scroll.mount(grid)

        # Title section
        with Container(classes="details-section"):
            grid.mount_child(Label("Current Title:"))
            grid.mount_child(
                Input(value=offer_data.title, disabled=True, id="detail-title-current")
            )
            grid.mount_child(Label("New Title:"))
            grid.mount_child(
                Input(
                    value=offer_data.title_new or offer_data.title,
                    placeholder="Enter new title",
                    id="detail-title-new",
                )
            )

        # Description section
        with Container(classes="details-section description-section"):
            grid.mount_child(Label("Current Description:"))
            grid.mount_child(
                MarkdownViewer(
                    offer_data.desc or "*No description available.*",
                    show_table_of_contents=False,
                    id="detail-desc-current",
                )
            )
            grid.mount_child(Label("New Description:"))
            grid.mount_child(
                TextArea(
                    offer_data.desc_new or offer_data.desc or "",
                    id="detail-desc-new",
                    show_line_numbers=False,
                )
            )

        # Try to refresh the footer if it exists
        try:
            if footer := self.query_one(Footer):
                footer.refresh()
        except Exception:
            pass  # Ignore footer refresh errors

    def action_back(self) -> None:
        """Hide the details panel."""
        if self.current_offer is not None:
            self.query_one("#details-container").remove_class("visible")
            self.current_offer = None
            # Ensure list view is focused
            self.query_one("#offer-table", DataTable).focus()
            # Try to refresh the footer if it exists
            try:
                if footer := self.query_one(Footer):
                    footer.refresh()
            except Exception:
                pass  # Ignore footer refresh errors

    def action_save_offer(self) -> None:
        """Handle save action."""
        if self.current_offer is None:
            return

        new_title = self.query_one("#detail-title-new", Input).value
        new_desc = self.query_one("#detail-desc-new", TextArea).text

        # Update both title and description
        if new_title != self.current_offer.title_new:
            cast(VolanteTUI, self.app).cli.set_title(
                self.current_offer.offer_id, new_title
            )
        if new_desc != self.current_offer.desc_new:
            cast(VolanteTUI, self.app).cli.set_desc(
                self.current_offer.offer_id, new_desc
            )

        # Refresh data
        self.current_offer = cast(VolanteTUI, self.app).db.get_offer(
            self.current_offer.offer_id
        )
        self.show_details(self.current_offer)
        self.app.notify("Changes saved locally")

    def action_publish_offer(self) -> None:
        """Handle publish action."""
        if self.current_offer is None:
            return

        cast(VolanteTUI, self.app).executor.execute_publish(self.current_offer.offer_id)
        self.current_offer = cast(VolanteTUI, self.app).db.get_offer(
            self.current_offer.offer_id
        )
        self.show_details(self.current_offer)
        self.app.notify("Changes published!")

    async def _refresh_offers(self) -> None:
        """Background worker for refreshing offers."""
        worker = get_current_worker()
        if worker and not worker.is_cancelled:
            self._toggle_progress(True)
            progress = self.query_one("#progress", ProgressBar)
            progress.update(progress=0)

            # Simulate progress during the operation
            for i in range(100):
                if worker.is_cancelled:
                    break
                await worker.sleep(0.05)  # Small delay
                progress.update(progress=i)

            cast(VolanteTUI, self.app).executor.execute_read_all()
            progress.update(progress=100)

    async def _publish_all(self) -> None:
        """Background worker for publishing all changes."""
        worker = get_current_worker()
        if worker and not worker.is_cancelled:
            self._toggle_progress(True)
            progress = self.query_one("#progress", ProgressBar)
            progress.update(progress=0)

            # Count pending changes
            pending = sum(
                1
                for offer in cast(VolanteTUI, self.app).db.data.values()
                if not offer.published and (offer.title_new or offer.desc_new)
            )

            if pending > 0:
                progress_step = 100 / pending
                current_progress = 0

                for offer in cast(VolanteTUI, self.app).db.data.values():
                    if worker.is_cancelled:
                        break
                    if not offer.published and (offer.title_new or offer.desc_new):
                        cast(VolanteTUI, self.app).executor.execute_publish(
                            offer.offer_id
                        )
                        current_progress += progress_step
                        progress.update(progress=min(int(current_progress), 100))
                        await worker.sleep(0.1)  # Small delay between publishes

            progress.update(progress=100)

    def action_refresh_offers(self) -> None:
        """Refreshes the offers from the website."""
        try:
            loading = self.query_one("#loading", LoadingIndicator)
            progress = self.query_one("#progress", ProgressBar)
            loading.display = True
            progress.display = True

            self.app.run_worker(
                self._refresh_offers(),
                group="refresh",
                description="Refreshing offers...",
                completion_handler=self._on_refresh_complete,
            )
        except Exception as e:
            self.app.notify(f"Error refreshing offers: {e}", severity="error")
            loading = self.query_one("#loading", LoadingIndicator)
            progress = self.query_one("#progress", ProgressBar)
            loading.display = False
            progress.display = False

    def _on_refresh_complete(self, worker: Worker) -> None:
        """Handle completion of refresh worker."""
        self._toggle_progress(False)
        if worker.is_cancelled:
            self.app.notify("Refresh cancelled", severity="warning")
        elif worker.error is not None:
            self.app.notify(
                f"Error refreshing offers: {worker.error}", severity="error"
            )
        else:
            self.refresh_offers_list()
            self.app.notify("Offers Refreshed!")

    def action_publish_all(self) -> None:
        """Publishes all pending changes."""
        try:
            loading = self.query_one("#loading", LoadingIndicator)
            progress = self.query_one("#progress", ProgressBar)
            loading.display = True
            progress.display = True

            self.app.run_worker(
                self._publish_all(),
                group="publish",
                description="Publishing changes...",
                completion_handler=self._on_publish_complete,
            )
        except Exception as e:
            self.app.notify(f"Error publishing changes: {e}", severity="error")
            loading = self.query_one("#loading", LoadingIndicator)
            progress = self.query_one("#progress", ProgressBar)
            loading.display = False
            progress.display = False

    def _on_publish_complete(self, worker: Worker) -> None:
        """Handle completion of publish worker."""
        self._toggle_progress(False)
        if worker.is_cancelled:
            self.app.notify("Publish cancelled", severity="warning")
        elif worker.error is not None:
            self.app.notify(
                f"Error publishing changes: {worker.error}", severity="error"
            )
        else:
            self.refresh_offers_list()
            self.app.notify("All pending changes published!")

    def action_refresh_offer(self) -> None:
        """Handle refresh action for the currently selected offer."""
        if self.current_offer is None:
            return
        from typing import cast
        from volante_lokalnie.tui import VolanteTUI

        cast(VolanteTUI, self.app).executor.execute_read(self.current_offer.offer_id)
        self.current_offer = cast(VolanteTUI, self.app).db.get_offer(
            self.current_offer.offer_id
        )
        self.show_details(self.current_offer)
        self.app.notify("Offer refreshed!")

    def action_sort_offers(self) -> None:
        """Sort offers by the current column."""
        table = self.query_one("#offer-table", DataTable)
        if table.cursor_column is not None:
            table.sort(table.cursor_column)

    def action_view_details(self) -> None:
        """Show details of the currently selected offer."""
        table = self.query_one("#offer-table", DataTable)
        if table.cursor_row is not None:
            offer_id = table.get_row_at(table.cursor_row).key
            offer_data = cast(VolanteTUI, self.app).db.get_offer(offer_id)
            self.current_offer = offer_data
            self.show_details(offer_data)
            # Focus the new title input
            self.query_one("#detail-title-new").focus()

    def on_key(self, event) -> None:
        """Handle key events dynamically based on current view."""
        if hasattr(event, "handled") and event.handled:
            return
        if self.current_offer is None:
            if event.key == "p":
                self.action_publish_all()
                event.stop()
            elif event.key == "r":
                self.action_refresh_offers()
                event.stop()
        else:
            if event.key in ("escape", "b"):
                self.action_back()
                event.stop()
            elif event.key == "r":
                self.action_refresh_offer()
                event.stop()
            elif event.key in ("s", "enter"):
                self.action_save_offer()
                event.stop()
            elif event.key == "p":
                self.action_publish_offer()
                event.stop()

    def get_bindings(self) -> list[tuple[str, str, str]]:
        """Return active key bindings based on the current view.
        When no offer is selected, return base + list bindings; otherwise, base + details bindings."""
        if self.current_offer is None:
            return self.__class__.BINDINGS + self.__class__.LIST_BINDINGS
        else:
            return self.__class__.BINDINGS + self.__class__.DETAILS_BINDINGS

    def action_sort_by_title(self) -> None:
        """Sort offers by title."""
        table = self.query_one("#offer-table", DataTable)
        table.sort(0)

    def action_sort_by_price(self) -> None:
        """Sort offers by price."""
        table = self.query_one("#offer-table", DataTable)
        table.sort(1)

    def action_sort_by_views(self) -> None:
        """Sort offers by views."""
        table = self.query_one("#offer-table", DataTable)
        table.sort(2)

    def action_sort_by_status(self) -> None:
        """Sort offers by status."""
        table = self.query_one("#offer-table", DataTable)
        table.sort(3)


class VolanteTUI(App):
    """Main Textual app for managing Allegro Lokalnie offers."""

    CSS_PATH = Path(__file__).parent / "volante_lokalnie.tcss"  # Use absolute path
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("o", "open_database", "Open Database"),
        ("r", "refresh_offers", "Refresh All"),
        ("s", "sort_offers", "Sort"),
        ("1", "sort_by_title", "Sort by Title"),
        ("2", "sort_by_price", "Sort by Price"),
        ("3", "sort_by_views", "Sort by Views"),
        ("4", "sort_by_status", "Sort by Status"),
        ("p", "publish_all", "Publish All"),
        ("enter", "view_details", "View Details"),
    ]

    def __init__(self, *args, **kwargs):
        """Initialize the TUI app.

        Args:
            *args: Positional arguments for App
            **kwargs: Keyword arguments for App
        """
        super().__init__(*args, **kwargs)
        self.db = OfferDatabase(DB_FILE)  # Initialize database with proper path
        self.cli = VolanteCLI()  # Initialize Fire CLI
        self.executor = ScrapeExecutor(
            self.db, verbose=False, dryrun=False
        )  # Create executor

        # Ensure database file exists and is loaded
        if not DB_FILE.exists():
            # Create parent directories if they don't exist
            DB_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Create an empty database file
            self.db.save()
        else:
            # Load existing database
            self.db.load()

    def on_mount(self) -> None:
        """Set up the application on startup."""
        # Push main screen - it will handle its own initialization in its on_mount
        self.push_screen(MainScreen())

    def on_unmount(self) -> None:
        """Clean up when the app is closing."""
        # Save any pending changes
        self.db.save()
