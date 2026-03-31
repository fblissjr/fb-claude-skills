# trigger: tui
## TUI design principles (auto-loaded)
- Semantic color: max 4 colors per view. Green=success, red=error, yellow=warning, dim=secondary. Test with NO_COLOR=1.
- Responsive layout: zero hardcoded widths. Use Rich ratio + min_width. Test at 80, 120, 200 columns.
- Right component: match data shape to Rich component (Table for rows, Tree for hierarchy, Panel for text).
- Visual hierarchy: bold=headers, normal=data, dim=metadata. One border style per view.
- Progressive density: default fits 20 lines. --verbose adds detail. --json for machine output.
- For full methodology and code patterns, invoke /tui-design:tui-design.
