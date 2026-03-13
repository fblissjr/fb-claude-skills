import type { PluginResult } from "../types.js";
import { StatusDot } from "./StatusDot.js";

interface Props {
  plugins: PluginResult[];
}

export function PluginTable({ plugins }: Props) {
  return (
    <div className="table-wrapper">
      <table className="check-table">
        <thead>
          <tr>
            <th>Plugin</th>
            <th>Manifest</th>
            <th>Marketplace</th>
            <th>README</th>
          </tr>
        </thead>
        <tbody>
          {plugins.map((plugin) => (
            <tr key={plugin.name}>
              <td className="cell-name">{plugin.name}</td>
              <td className="cell-status">
                <StatusDot
                  passed={plugin.checks.manifestFields.passed}
                  title={plugin.checks.manifestFields.detail}
                />
              </td>
              <td className="cell-status">
                <StatusDot
                  passed={plugin.checks.marketplaceListing.passed}
                  title={plugin.checks.marketplaceListing.detail}
                />
              </td>
              <td className="cell-status">
                <StatusDot
                  passed={plugin.checks.readmeExists.passed}
                  title={plugin.checks.readmeExists.detail}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
