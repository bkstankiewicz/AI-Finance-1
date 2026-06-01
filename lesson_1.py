import argparse
import sys

DEFAULT_EXAMPLES = [
    argparse.Namespace(
        asset_class="equity",
        instrument="INTC",
        quantity=100,
        entry_price=20.0,
        current_price=120.0,
    ),
    argparse.Namespace(
        asset_class="bond",
        bond_name="Poland 10Y",
        position_size=25,
        bond_price=98.70,
        face_value=1000,
    ),
    argparse.Namespace(
        asset_class="fx",
        currency_pair="EUR/USD",
        notional_source=2_000_000,
        spot_rate=1.0825,
    ),
]

def equity_trade(args):
    market_value = args.quantity * args.current_price
    pnl = (args.current_price - args.entry_price) * args.quantity
    return {
        "Instrument": args.instrument,
        "Market value": market_value,
        "P&L": pnl
    }

def bond_trade(args):
    bond_market_value = (args.bond_price / 100) * args.face_value * args.position_size
    return {
        "Bond name": args.bond_name,
        "Bond market value": bond_market_value
    }

def fx_trade(args):
    notional_target = args.notional_source * args.spot_rate
    return {
        "Pair": args.currency_pair,
        "Notional target": notional_target
    }

def display(args, results):
    print(f"Asset class: {args.asset_class}")
    for key, value in results.items():
        print(f"{key}: {value}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Calculate the profit and loss (P&L) for different types of trades."
    )
    subparsers = parser.add_subparsers(dest="asset_class", required=True)

    subparser_args = {
    "equity": [
        ("instrument", str, "Name of the equity instrument"),
        ("quantity", int, "Quantity of shares"),
        ("entry_price", float, "Entry price per share"),
        ("current_price", float, "Current price per share"),
        ],
    "bond": [
        ("bond_name", str, "Name of the bond e.g. Poland 10Y"),
        ("position_size", int, "Quantity of bonds"),
        ("bond_price", float, "Bond price"),
        ("face_value", float, "Face value of the bond"),
        ],
    "fx": [
        ("currency_pair", str, "Currency pair e.g. EUR/USD"),
        ("notional_source", float, "Notional in source currency"),
        ("spot_rate", float, "Spot rate"),
        ],
    }

    for asset_class, arguments in subparser_args.items():
        sub = subparsers.add_parser(asset_class, help=f"{asset_class} trade")
        for name, type, help in arguments:
            sub.add_argument(name, type=type, help=help)

    return parser.parse_args()


if __name__ == "__main__":
    trade_functions = {
        "equity": equity_trade,
        "bond": bond_trade,
        "fx": fx_trade,
    }

    use_defaults = len(sys.argv) == 1

    if use_defaults:
        print("[INFO] Used default values.\n")
        for args in DEFAULT_EXAMPLES:
            results = trade_functions[args.asset_class](args)
            display(args, results)
            print("\n")
    else:
        args = parse_arguments()
        results = trade_functions[args.asset_class](args)
        display(args, results)
