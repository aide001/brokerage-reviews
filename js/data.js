/*
 * Broker dataset.
 *
 * IMPORTANT: Figures below are approximate, collected for demonstration, and
 * change frequently (spreads, deposits and leverage also vary by country and by
 * the legal entity a client is onboarded with). Verify every value against each
 * broker's official website before publishing this site.
 *
 * Field notes:
 *   spread      Typical EUR/USD spread in pips on the account type listed.
 *   commission  Round-turn commission in USD per standard lot (100k units).
 *   leverage    Maximum leverage offered to retail clients by any group entity.
 *   ratings     Editorial scores out of 5.
 *   domain      Official website, used by scripts/fetch-logos.sh.
 *
 * Logos: put a square logo at assets/logos/<id>.svg or assets/logos/<id>.png.
 * If neither file exists, the broker's initials are shown instead.
 */
window.BROKERS = [
  {
    id: "ic-markets",
    domain: "icmarkets.com",
    name: "IC Markets",
    color: "#1b75bb",
    founded: 2007,
    hq: "Sydney, Australia",
    regulators: ["ASIC", "CySEC", "FSA (SC)"],
    minDeposit: 200,
    account: "Raw Spread",
    spread: 0.1,
    commission: 7,
    leverage: 500,
    platforms: ["MT4", "MT5", "cTrader", "TradingView"],
    instruments: 2250,
    bestFor: "Low-cost ECN trading",
    ratings: { fees: 4.9, platforms: 4.7, trust: 4.3, support: 4.4, education: 3.8 },
    pros: [
      "Very tight raw spreads on major pairs",
      "Choice of MT4, MT5, cTrader and TradingView",
      "Fast execution suited to scalping and EAs"
    ],
    cons: [
      "Limited proprietary research",
      "Higher leverage only via offshore entity",
      "Education section is basic"
    ],
    summary:
      "IC Markets is a popular choice for active and algorithmic traders thanks to raw pricing, deep liquidity and a strong line-up of third-party platforms."
  },
  {
    id: "pepperstone",
    domain: "pepperstone.com",
    name: "Pepperstone",
    color: "#0f2a4a",
    founded: 2010,
    hq: "Melbourne, Australia",
    regulators: ["ASIC", "FCA", "CySEC", "BaFin", "DFSA", "CMA", "SCB"],
    minDeposit: 0,
    account: "Razor",
    spread: 0.1,
    commission: 7,
    leverage: 200,
    platforms: ["MT4", "MT5", "cTrader", "TradingView"],
    instruments: 1300,
    bestFor: "Active traders wanting top-tier regulation",
    ratings: { fees: 4.8, platforms: 4.8, trust: 4.8, support: 4.6, education: 4.2 },
    pros: [
      "Regulated by several tier-1 authorities",
      "Razor account offers raw spreads",
      "No minimum deposit"
    ],
    cons: [
      "No proprietary platform",
      "Product range narrower than multi-asset brokers",
      "No guaranteed stop-loss in most regions"
    ],
    summary:
      "Pepperstone combines low trading costs with some of the broadest regulatory coverage in the industry, making it a well-rounded choice for most forex traders."
  },
  {
    id: "oanda",
    domain: "oanda.com",
    name: "OANDA",
    color: "#1a1a1a",
    founded: 1996,
    hq: "New York, USA",
    regulators: ["CFTC/NFA", "FCA", "ASIC", "CIRO", "MAS"],
    minDeposit: 0,
    account: "Standard",
    spread: 1.2,
    commission: 0,
    leverage: 200,
    platforms: ["OANDA Trade", "MT4", "TradingView"],
    instruments: 120,
    bestFor: "US traders and beginners",
    ratings: { fees: 4.0, platforms: 4.4, trust: 4.9, support: 4.3, education: 4.4 },
    pros: [
      "Long track record and strong regulation, including the US",
      "No minimum deposit",
      "Excellent historical FX data and research"
    ],
    cons: [
      "Standard spreads higher than ECN brokers",
      "Smaller range of non-FX instruments",
      "US leverage limited to 1:50"
    ],
    summary:
      "OANDA is one of the most established forex brokers, trusted for transparent pricing and available to US residents, with solid tools for newer traders."
  },
  {
    id: "forex-com",
    domain: "forex.com",
    name: "FOREX.com",
    color: "#00a651",
    founded: 2001,
    hq: "New Jersey, USA",
    regulators: ["CFTC/NFA", "FCA", "ASIC", "CIRO", "CIMA"],
    minDeposit: 100,
    account: "Standard",
    spread: 1.2,
    commission: 0,
    leverage: 50,
    platforms: ["FOREX.com Web", "MT4", "MT5", "TradingView"],
    instruments: 500,
    bestFor: "Wide choice of currency pairs",
    ratings: { fees: 4.1, platforms: 4.5, trust: 4.8, support: 4.2, education: 4.3 },
    pros: [
      "80+ currency pairs",
      "Part of publicly listed StoneX group",
      "Good in-house research and platform"
    ],
    cons: [
      "Standard spreads not the lowest",
      "Inactivity fee applies",
      "Account types vary by region"
    ],
    summary:
      "FOREX.com offers one of the widest selections of FX pairs, US availability and strong corporate backing, with a capable proprietary platform."
  },
  {
    id: "ig",
    domain: "ig.com",
    name: "IG",
    color: "#e2001a",
    founded: 1974,
    hq: "London, UK",
    regulators: ["FCA", "ASIC", "BaFin", "CFTC/NFA", "MAS", "FINMA"],
    minDeposit: 0,
    account: "CFD Standard",
    spread: 0.85,
    commission: 0,
    leverage: 200,
    platforms: ["IG Platform", "MT4", "ProRealTime", "TradingView"],
    instruments: 17000,
    bestFor: "Overall best all-rounder",
    ratings: { fees: 4.3, platforms: 4.8, trust: 5.0, support: 4.5, education: 4.8 },
    pros: [
      "Huge range of markets",
      "Decades-long history, listed on the LSE",
      "Top-class education and research"
    ],
    cons: [
      "Complex fee structure for some products",
      "Platform can feel overwhelming to beginners",
      "Inactivity fee after two years"
    ],
    summary:
      "IG is a global heavyweight offering an enormous range of markets, excellent tools and research, and exceptional regulatory standing."
  },
  {
    id: "xtb",
    domain: "xtb.com",
    name: "XTB",
    color: "#d71920",
    founded: 2002,
    hq: "Warsaw, Poland",
    regulators: ["KNF", "FCA", "CySEC", "FSC (BZ)"],
    minDeposit: 0,
    account: "Standard",
    spread: 0.9,
    commission: 0,
    leverage: 500,
    platforms: ["xStation 5"],
    instruments: 7000,
    bestFor: "Beginners wanting a great app",
    ratings: { fees: 4.4, platforms: 4.6, trust: 4.5, support: 4.7, education: 4.7 },
    pros: [
      "Award-winning xStation platform",
      "Strong education library",
      "Publicly listed on the Warsaw Stock Exchange"
    ],
    cons: [
      "No MT4/MT5 support",
      "Limited automated trading options",
      "Not available in the US"
    ],
    summary:
      "XTB is a user-friendly broker built around its excellent xStation platform, with commission-free standard pricing and very good educational content."
  },
  {
    id: "etoro",
    domain: "etoro.com",
    name: "eToro",
    color: "#13c636",
    founded: 2007,
    hq: "Tel Aviv, Israel",
    regulators: ["FCA", "CySEC", "ASIC", "FSAS"],
    minDeposit: 50,
    account: "Standard",
    spread: 1.0,
    commission: 0,
    leverage: 30,
    platforms: ["eToro Platform"],
    instruments: 5000,
    bestFor: "Social and copy trading",
    ratings: { fees: 3.8, platforms: 4.4, trust: 4.4, support: 3.9, education: 4.1 },
    pros: [
      "Industry-leading copy trading",
      "Very easy to use",
      "Stocks, ETFs and crypto in one account"
    ],
    cons: [
      "Wider forex spreads",
      "Withdrawal and conversion fees",
      "No MetaTrader support"
    ],
    summary:
      "eToro is the go-to platform for social and copy trading, trading off slightly higher FX costs for simplicity and community features."
  },
  {
    id: "interactive-brokers",
    domain: "interactivebrokers.com",
    name: "Interactive Brokers",
    color: "#d81222",
    founded: 1978,
    hq: "Greenwich, USA",
    regulators: ["SEC", "CFTC/NFA", "FCA", "ASIC", "CBI", "MAS"],
    minDeposit: 0,
    account: "IBKR Pro",
    spread: 0.2,
    commission: 4,
    leverage: 50,
    platforms: ["Trader Workstation", "IBKR Desktop", "API"],
    instruments: 1000000,
    bestFor: "Professionals and large accounts",
    ratings: { fees: 4.8, platforms: 4.5, trust: 5.0, support: 4.0, education: 4.3 },
    pros: [
      "Interbank-style FX pricing",
      "Access to global exchanges",
      "Exceptional financial strength"
    ],
    cons: [
      "Steep learning curve",
      "Complex fee schedule",
      "Customer support can be slow"
    ],
    summary:
      "Interactive Brokers delivers institutional-grade pricing and market access, best suited to experienced traders comfortable with advanced tools."
  },
  {
    id: "saxo",
    domain: "home.saxo",
    name: "Saxo",
    color: "#0038a8",
    founded: 1992,
    hq: "Copenhagen, Denmark",
    regulators: ["DFSA (DK)", "FCA", "ASIC", "MAS", "FINMA"],
    minDeposit: 0,
    account: "Classic",
    spread: 0.9,
    commission: 0,
    leverage: 30,
    platforms: ["SaxoTraderGO", "SaxoTraderPRO", "TradingView"],
    instruments: 71000,
    bestFor: "Multi-asset investors",
    ratings: { fees: 4.2, platforms: 4.9, trust: 4.9, support: 4.3, education: 4.4 },
    pros: [
      "Superb in-house platforms",
      "Enormous multi-asset product range",
      "Licensed bank in Denmark"
    ],
    cons: [
      "Better pricing needs higher account tiers",
      "No MetaTrader",
      "Custody fees on some holdings"
    ],
    summary:
      "Saxo is a Danish bank offering premium trading platforms and one of the largest product line-ups available to retail traders."
  },
  {
    id: "cmc-markets",
    domain: "cmcmarkets.com",
    name: "CMC Markets",
    color: "#0f6e84",
    founded: 1989,
    hq: "London, UK",
    regulators: ["FCA", "ASIC", "CIRO", "MAS", "BaFin"],
    minDeposit: 0,
    account: "CFD Standard",
    spread: 0.7,
    commission: 0,
    leverage: 30,
    platforms: ["Next Generation", "MT4", "TradingView"],
    instruments: 12000,
    bestFor: "Charting and technical analysis",
    ratings: { fees: 4.5, platforms: 4.8, trust: 4.9, support: 4.3, education: 4.4 },
    pros: [
      "Excellent charting tools",
      "Competitive standard spreads",
      "Listed on the London Stock Exchange"
    ],
    cons: [
      "Many features can overwhelm new traders",
      "MT4 has fewer instruments",
      "Not available in the US"
    ],
    summary:
      "CMC Markets pairs competitive pricing with a feature-rich Next Generation platform that technical traders will appreciate."
  },
  {
    id: "exness",
    domain: "exness.com",
    name: "Exness",
    color: "#f5c400",
    founded: 2008,
    hq: "Limassol, Cyprus",
    regulators: ["CySEC", "FCA", "FSCA", "FSA (SC)"],
    minDeposit: 10,
    account: "Standard",
    spread: 1.0,
    commission: 0,
    leverage: 2000,
    platforms: ["MT4", "MT5", "Exness Terminal"],
    instruments: 250,
    bestFor: "Small accounts and instant withdrawals",
    ratings: { fees: 4.4, platforms: 4.3, trust: 4.0, support: 4.5, education: 3.6 },
    pros: [
      "Very low $10 minimum deposit",
      "Fast, often instant withdrawals",
      "Wide range of account types"
    ],
    cons: [
      "Very high leverage only via offshore entities",
      "Limited research and education",
      "Smaller product range"
    ],
    summary:
      "Exness appeals to traders starting small, with a low minimum deposit, flexible accounts and a reputation for fast withdrawals."
  },
  {
    id: "avatrade",
    domain: "avatrade.com",
    name: "AvaTrade",
    color: "#2a3b8f",
    founded: 2006,
    hq: "Dublin, Ireland",
    regulators: ["CBI", "ASIC", "FSCA", "FSA (JP)", "ADGM"],
    minDeposit: 100,
    account: "Standard (fixed)",
    spread: 0.9,
    commission: 0,
    leverage: 400,
    platforms: ["MT4", "MT5", "AvaTradeGO", "WebTrader"],
    instruments: 1250,
    bestFor: "Fixed spreads and risk management",
    ratings: { fees: 4.1, platforms: 4.3, trust: 4.5, support: 4.2, education: 4.4 },
    pros: [
      "Fixed spreads offer cost certainty",
      "AvaProtect trade insurance feature",
      "Regulated across several continents"
    ],
    cons: [
      "Inactivity and administration fees",
      "No raw-spread account",
      "Research is fairly basic"
    ],
    summary:
      "AvaTrade offers predictable fixed spreads and useful risk-management features, backed by regulation across multiple jurisdictions."
  },
  {
    id: "ironfx",
    domain: "ironfx.com",
    name: "IronFX",
    color: "#0d3b78",
    founded: 2010,
    hq: "Limassol, Cyprus",
    regulators: ["FCA", "CySEC", "ASIC", "FSCA"],
    minDeposit: 50,
    account: "Standard (floating)",
    spread: 1.2,
    commission: 0,
    leverage: 1000,
    platforms: ["MT4", "MT5", "WebTrader"],
    instruments: 300,
    bestFor: "Bonuses and account variety",
    ratings: { fees: 4.0, platforms: 4.0, trust: 3.9, support: 4.1, education: 4.0 },
    pros: [
      "Licensed by FCA, CySEC and ASIC",
      "Wide choice of fixed, floating and zero-spread accounts",
      "Low $50 minimum deposit"
    ],
    cons: [
      "Mixed reputation from past client complaints",
      "Standard spreads wider than raw-pricing brokers",
      "High leverage only through offshore entities"
    ],
    summary:
      "IronFX offers a broad menu of account types and MetaTrader platforms under several regulators, but its standard pricing is not the cheapest and its reputation is mixed."
  },
  {
    id: "pu-prime",
    domain: "puprime.com",
    name: "PU Prime",
    color: "#0b2447",
    founded: 2015,
    hq: "Victoria, Seychelles",
    regulators: ["ASIC", "FSCA", "FSC (MU)", "FSA (SC)"],
    minDeposit: 50,
    account: "Standard",
    spread: 1.3,
    commission: 0,
    leverage: 1000,
    platforms: ["MT4", "MT5", "PU Prime App", "WebTrader"],
    instruments: 1000,
    bestFor: "High leverage and copy trading",
    ratings: { fees: 4.0, platforms: 4.2, trust: 3.6, support: 4.3, education: 3.8 },
    pros: [
      "Low $50 minimum deposit ($20 on Cent)",
      "Copy trading and a capable mobile app",
      "Up to 1:1000 leverage offshore"
    ],
    cons: [
      "Most international clients onboarded via Seychelles entity",
      "FCA has issued a warning about the Seychelles entity",
      "Prime and ECN accounts need large deposits"
    ],
    summary:
      "PU Prime (formerly Pacific Union) targets active traders with high leverage and copy trading, though most clients are served by its lightly regulated offshore entity."
  },
  {
    id: "xm",
    domain: "xm.com",
    name: "XM",
    color: "#d51820",
    founded: 2009,
    hq: "Limassol, Cyprus",
    regulators: ["CySEC", "ASIC", "DFSA", "FSC (BZ)"],
    minDeposit: 5,
    account: "Standard",
    spread: 1.6,
    commission: 0,
    leverage: 1000,
    platforms: ["MT4", "MT5", "XM App"],
    instruments: 1400,
    bestFor: "Very small starting deposits",
    ratings: { fees: 3.9, platforms: 4.3, trust: 4.2, support: 4.5, education: 4.6 },
    pros: [
      "$5 minimum deposit",
      "Strong free education and webinars",
      "Multilingual 24/5 support"
    ],
    cons: [
      "Standard account spreads are wide",
      "High leverage only via Belize entity",
      "Not available in the US"
    ],
    summary:
      "XM is a beginner-friendly broker with a tiny minimum deposit and excellent educational content, offset by relatively wide spreads on its standard account."
  },
  {
    id: "vantage",
    domain: "vantagemarkets.com",
    name: "Vantage",
    color: "#0b1a33",
    founded: 2009,
    hq: "Sydney, Australia",
    regulators: ["ASIC", "FCA", "CIMA", "VFSC"],
    minDeposit: 50,
    account: "Raw ECN",
    spread: 0.1,
    commission: 6,
    leverage: 500,
    platforms: ["MT4", "MT5", "TradingView", "ProTrader"],
    instruments: 1000,
    bestFor: "Low-cost raw pricing",
    ratings: { fees: 4.6, platforms: 4.5, trust: 4.1, support: 4.3, education: 4.0 },
    pros: [
      "Raw spreads with a $6 round-turn commission",
      "TradingView and copy trading integration",
      "Low $50 minimum deposit"
    ],
    cons: [
      "Most clients served by offshore entities",
      "Limited research output",
      "Product range varies by region"
    ],
    summary:
      "Vantage combines tight raw pricing and modern platform choices with a low entry point, making it a solid option for cost-conscious traders."
  },
  {
    id: "fp-markets",
    domain: "fpmarkets.com",
    name: "FP Markets",
    color: "#1a2f5a",
    founded: 2005,
    hq: "Sydney, Australia",
    regulators: ["ASIC", "CySEC", "FSCA", "FSA (SC)"],
    minDeposit: 100,
    account: "Raw",
    spread: 0.1,
    commission: 6,
    leverage: 500,
    platforms: ["MT4", "MT5", "cTrader", "TradingView"],
    instruments: 10000,
    bestFor: "Raw spreads on every major platform",
    ratings: { fees: 4.7, platforms: 4.6, trust: 4.4, support: 4.5, education: 4.1 },
    pros: [
      "Very low raw-account costs",
      "MT4, MT5, cTrader and TradingView",
      "Large range including share CFDs"
    ],
    cons: [
      "Share CFD range limited on MT4",
      "No proprietary platform",
      "Higher leverage via offshore entity only"
    ],
    summary:
      "FP Markets is a long-running Australian broker offering some of the lowest raw trading costs across all the popular third-party platforms."
  },
  {
    id: "tickmill",
    domain: "tickmill.com",
    name: "Tickmill",
    color: "#0e2a47",
    founded: 2014,
    hq: "London, UK",
    regulators: ["FCA", "CySEC", "FSCA", "DFSA", "FSA (SC)"],
    minDeposit: 100,
    account: "Raw",
    spread: 0.1,
    commission: 6,
    leverage: 500,
    platforms: ["MT4", "MT5", "TradingView"],
    instruments: 600,
    bestFor: "Scalpers and algo traders",
    ratings: { fees: 4.8, platforms: 4.3, trust: 4.4, support: 4.2, education: 4.0 },
    pros: [
      "Among the lowest raw commissions",
      "FCA and CySEC regulated",
      "Fast execution, EA-friendly"
    ],
    cons: [
      "Smaller product range",
      "No proprietary platform",
      "Research is fairly basic"
    ],
    summary:
      "Tickmill is built for cost-sensitive active traders, with very low raw commissions and fast execution under solid regulation."
  },
  {
    id: "hfm",
    domain: "hfm.com",
    name: "HFM",
    color: "#d0121b",
    founded: 2010,
    hq: "Limassol, Cyprus",
    regulators: ["CySEC", "FCA", "FSCA", "DFSA", "FSA (SC)", "CMA"],
    minDeposit: 0,
    account: "Premium",
    spread: 1.4,
    commission: 0,
    leverage: 2000,
    platforms: ["MT4", "MT5", "HFM App"],
    instruments: 1000,
    bestFor: "Account flexibility and promotions",
    ratings: { fees: 4.0, platforms: 4.3, trust: 4.2, support: 4.4, education: 4.3 },
    pros: [
      "No minimum deposit on Premium account",
      "Wide range of account types",
      "Good education and market analysis"
    ],
    cons: [
      "Premium spreads are wide",
      "Very high leverage only offshore",
      "Website and account types can be confusing"
    ],
    summary:
      "HFM (formerly HotForex) offers lots of account options and trading tools across many jurisdictions, though its standard pricing is on the high side."
  },
  {
    id: "fxtm",
    domain: "forextime.com",
    name: "FXTM",
    color: "#c4d600",
    founded: 2011,
    hq: "Limassol, Cyprus",
    regulators: ["CySEC", "FCA", "FSC (MU)", "CMA"],
    minDeposit: 200,
    account: "Advantage",
    spread: 0.1,
    commission: 8,
    leverage: 2000,
    platforms: ["MT4", "MT5", "FXTM Trader"],
    instruments: 1000,
    bestFor: "Emerging-market traders",
    ratings: { fees: 4.3, platforms: 4.2, trust: 4.1, support: 4.2, education: 4.4 },
    pros: [
      "Advantage account offers raw spreads",
      "Strong presence in Africa and Asia",
      "Good educational resources"
    ],
    cons: [
      "Commission higher than the cheapest ECN brokers",
      "Most clients served by Mauritius entity",
      "Limited non-FX range"
    ],
    summary:
      "FXTM (ForexTime) has a strong following in emerging markets, pairing raw-spread accounts with helpful education and local support."
  },
  {
    id: "axi",
    domain: "axi.com",
    name: "Axi",
    color: "#e3002b",
    founded: 2007,
    hq: "Sydney, Australia",
    regulators: ["ASIC", "FCA", "DFSA", "FMA"],
    minDeposit: 0,
    account: "Pro",
    spread: 0.1,
    commission: 7,
    leverage: 500,
    platforms: ["MT4", "Axi Copy"],
    instruments: 140,
    bestFor: "MT4 traders wanting strong regulation",
    ratings: { fees: 4.5, platforms: 4.0, trust: 4.6, support: 4.4, education: 4.1 },
    pros: [
      "No minimum deposit",
      "Raw-spread Pro account",
      "Regulated in the UK, Australia and New Zealand"
    ],
    cons: [
      "MT4 only, no MT5",
      "Smaller instrument range",
      "Limited research"
    ],
    summary:
      "Axi is a well-regulated, no-frills MetaTrader 4 broker with competitive raw pricing and no minimum deposit."
  }
];

// Regulators generally regarded as "tier-1" for the trust filter.
window.TIER1_REGULATORS = [
  "FCA", "ASIC", "CFTC/NFA", "SEC", "BaFin", "FINMA", "MAS", "CIRO", "CBI", "DFSA (DK)", "FSA (JP)"
];
