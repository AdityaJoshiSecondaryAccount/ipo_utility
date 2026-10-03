11-09-2026 -> startes

19-09-2026 -> 1. Trades page Started
22-09-2026 -> Trades page ended

23-09-2026 -> 
1. Added search in Client Setup page and fixed initial load
2. Added search in Group Setup page
3. Added total row in Accounting modal
4. Added conditional dull style to IPO cards
5. Fixed dashboard focus and GWD filter issues

25-09-2026 -> 
1. Added search & fixed auto-fill search in GroupWise Dashboard (GWD)
2. Updated double-click functionality in GroupWise Dashboard
3. Hide Investor column in Order Details (Buy/Sell) when whole column is '0'
4. Added dynamic export filename in Billing page
5. Added tooltip to Trades page orange rows
6. Centralized and added dynamic dropdown filters across multiple pages
7. Added keyboard date editing with automated input masking in Trades page
8. Enhanced conditional styling for IPO cards on Home page
9. Added global top margin (33px) for alert/toast banners across all pages
10. Fixed responsive layout, gap, and button overflow for Place Order buttons in Buy and Sell pages
11. Updated JV functionality in transfer payment model
12. Miscellaneous CSS updates

26-09-2026 ->
1. Implemented auto-submit functionality (`onchange="this.form.submit()"`) for filter dropdowns across Accounting, OrderDetail (Buy & Sell), and Billing pages
2. Hidboth redundant Search buttons across the mentioned modules to streamline the auto-filter user experience
3. Overhauled Group Wise Dashboard (GWD) table layout using strict CSS classes to prevent distortion during column toggling.
4. Implemented dynamic column widths with `max-content` and text ellipsis (`...`) for cleaner cell wrapping in GWD.
5. Standardized `tfoot` widths to seamlessly align with headers and body in GWD.
6. Embedded numerical data-sort attributes (`data-sort`, `sorttable_customkey`) in GWD table to properly sort columns by Due Amount rather than alphabetical text.
7. Fixed overflow issues on Home page cards by cleanly truncating very long IPO names using Django slice tags (`[:12]`) and adding hover tooltips.
8. Enhanced mobile responsiveness on Home page by hiding status text ("Listed"/"In-progress") and reshaping the status indicator into a compact pulse circle on small screens.
9. Standardized CSS styles for the Bulk Order modal.

28-09-2026 ->
1. Implemented full server-side sorting (sorting the whole table instead of just visible rows) across all major pages: Trades, Orders, Billing, Group Wise Dashboard (GWD), App Buy/Sell Order, OrderDetail, Group Details, and IPO Setup.
2. Fixed pagination issues in `status.html`.
3. Fixed and refined the keyboard shortcuts tooltip styling in the Trades page.
4. Optimized pagination UX by removing session-based `page_size` storage, auto-falling back to 50 items per page upon re-entry to prevent heavy loads.
5. Added new toggle functionality and removed obsolete/unwanted code to clean up the codebase.
 
29-09-2026 ->
1. Fixed navbar overlapping layout issues by adding proper top padding to page wrappers (`trades.html`).
2. Fixed long dynamic title text (`.iponame`) from wrapping and breaking the header layout on small screens by adding strict text ellipsis CSS.
3. Prevented navbar navigation links from wrapping on medium screens by forcing `white-space: nowrap` and using Bootstrap responsive display classes (dynamically changing "Group Wise Dashboard" to "GWD").
4. Added dropdown for Rates in Order page.
5. On refresh clear Sort & page info.

30-09-2026 ->
1. Optimized `GroupWiseDashboard.html` layout by calculating dynamic column widths for the Group Name header, capping at 160px with `text-overflow: ellipsis` to avoid excessive whitespace while preventing overflow.
2. Improved responsive layout in `Order.html` by adding a jQuery resize listener that moves the "Show Rows" dropdown: keeps it left of filters on wide screens, and drops it into the second row alongside the Search box on smaller screens (< 1200px).
3. Enhanced Home page (`index.html`) IPO name truncation by dropping hardcoded Django slices (`[:15]`) in favor of dynamic CSS `text-overflow: ellipsis` (`calc(100% - 95px)`), ensuring text never overlaps the absolutely positioned status badges regardless of exact character count.
4. Added new tiered CSS media queries (1650px, 1171px, 900px) in `index.html` to smoothly transition the status badge (Listed/In-progress) from full text to a compact indicator dot as the screen shrinks.
5. Implemented global server-side search across all records in the `Order` page with a custom debounce and seamless focus retention.
6. Combined the Checkbox and "Sr. No" columns into a single space-saving column in the `IPOSETUP` page.
7. Fixed the CSS layout in `GroupSetup.html` to ensure the Search label always stacks vertically above its input field.
8. Replicated the seamless global server-side search functionality from Orders directly into the `IPOSETUP` page.
9. Dynamically updated the "IPO Status" modal title in the `Order` page to reflect the active group filter (e.g. `IPO Status - [groupname]`).
10. Fixed a critical usability bug across all Dashboard variants where hitting "Enter" failed to submit forms due to restrictive keypress interceptors.

1-10-2026 ->
1. Implemented an auto-reset feature in `OrderDetail` and `OrderDetail - Sell` pages that automatically resets the Order Category, Investor Type, and Rate dropdowns to "All" whenever the Group Name filter is changed, ensuring clean filtering.
2. Resolved a critical "Session Conflict" bug where authenticated brokers opening a guest "Shared Link" would have their normal workspace restricted by lingering guest session flags. Restricted guest access is now strictly bound to the `/access-link/` URL path.

2-10-2026 ->
1. Added "Copy to Clipboard" functionality in the `Status.html` dashboard, allowing users to instantly copy formatted Kostak, Subject To, and Premium share values.
2. Refactored the "Copy Shares" feature to extract accurate share numbers via robust `data-*` attributes injected from `views.py`, resolving formatting and alignment issues on smaller screens.
3. Merged critical backend updates into `views.py` (improved scraping mechanisms and API logic).
4. Added a "Sr. No" column and a "Refresh" button to the `OrderDetail` and `OrderDetail - Sell` pages.
5. Changed the date and time format displays in the `OrderDetail` pages.
6. Fixed the "Page Size" reset bug in `OrderDetail` pages.
7. Fixed a loader visibility issue in `Cdashboard.html`.





## WhatsApp Cloud API

Set these environment variables before starting the application:

- `WHATSAPP_API_VERSION` (defaults to `v21.0`)
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_ACCESS_TOKEN` (`WHATSAPP_API_KEY` is also accepted for compatibility)

The approved Meta template must be named `ipo_order_confirmation` and use the
named body parameters defined in `whatsapp/client.py`.