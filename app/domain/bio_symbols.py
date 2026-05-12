"""Hand-written SVG symbol library for bio/chem schematics.

23 reusable symbols covering common molecular-pathway entities. Path A's
system prompt advertises this catalog; outputs reference symbols via
`<use href="#<id>" x="..." y="..." width="..." height="..."/>`.

Style conventions (BioRender-inspired):
- Receptors / membrane proteins: light blue fill (#A8C5E2), dark blue stroke (#3A5F7F)
- Cytosolic enzymes: green fill (#B5D4A8), green stroke (#4A7A3F)
- Ions / charge carriers: light purple fill (#D4B8E2), purple stroke (#7F4A9C)
- Energy currency (ATP/ADP/cAMP): warm yellow fill (#FFE8B0), amber stroke (#C8901F)
- Lipids / membrane: peach fill (#FFD4B0), orange stroke (#C86B1F)
- Modifications: bright accent (P=red, Ub=purple, Ac=green)
- Organelles: pastel fill, contrasting stroke
- Stroke-width: 1.5 baseline, 2.0 for primary outlines, 2.5 for organelle perimeter
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolEntry:
    id: str
    name: str
    category: str
    use_when: str
    default_w: int
    default_h: int


# ── Symbol SVG strings ────────────────────────────────────────────────────

_RECEPTORS: dict[str, str] = {
    "gpcr": """<symbol id="gpcr" viewBox="0 0 60 80" overflow="visible">
        <rect x="5" y="5" width="50" height="70" rx="6"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <path d="M 12 14 L 48 22 L 12 30 L 48 38 L 12 46 L 48 54 L 12 62 L 48 70"
              fill="none" stroke="#3A5F7F" stroke-width="1.5" opacity="0.8"/>
    </symbol>""",
    "rtk": """<symbol id="rtk" viewBox="0 0 60 100" overflow="visible">
        <rect x="10" y="5" width="40" height="32" rx="4"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <rect x="22" y="37" width="16" height="22"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <ellipse cx="30" cy="78" rx="22" ry="16"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="2"/>
        <text x="30" y="83" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif"
              font-size="11" fill="#4A7A3F" font-weight="bold">K</text>
    </symbol>""",
    "ion_channel": """<symbol id="ion_channel" viewBox="0 0 60 80" overflow="visible">
        <rect x="3" y="5" width="22" height="70" rx="4"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <rect x="35" y="5" width="22" height="70" rx="4"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
    </symbol>""",
    "transporter": """<symbol id="transporter" viewBox="0 0 60 80" overflow="visible">
        <rect x="5" y="5" width="50" height="70" rx="6"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <path d="M 30 68 L 30 16 M 22 24 L 30 14 L 38 24"
              fill="none" stroke="#3A5F7F" stroke-width="2" stroke-linecap="round"/>
    </symbol>""",
    "generic_membrane_protein": """<symbol id="generic_membrane_protein" viewBox="0 0 60 80" overflow="visible">
        <rect x="5" y="5" width="50" height="70" rx="8"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
    </symbol>""",
}

_ENZYMES: dict[str, str] = {
    "kinase": """<symbol id="kinase" viewBox="0 0 80 50" overflow="visible">
        <ellipse cx="40" cy="25" rx="35" ry="20"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="2"/>
    </symbol>""",
    "phosphatase": """<symbol id="phosphatase" viewBox="0 0 80 50" overflow="visible">
        <ellipse cx="40" cy="25" rx="35" ry="20"
              fill="#E8C5B5" stroke="#9C5F47" stroke-width="2"/>
    </symbol>""",
    "generic_protein": """<symbol id="generic_protein" viewBox="0 0 80 50" overflow="visible">
        <rect x="5" y="5" width="70" height="40" rx="20"
              fill="#D4D4D4" stroke="#666666" stroke-width="2"/>
    </symbol>""",
    "complex": """<symbol id="complex" viewBox="0 0 110 60" overflow="visible">
        <ellipse cx="30" cy="30" rx="25" ry="18"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="2"/>
        <ellipse cx="62" cy="30" rx="25" ry="18"
              fill="#A8C5D4" stroke="#4A6F7F" stroke-width="2"/>
        <ellipse cx="88" cy="30" rx="20" ry="14"
              fill="#D4C5A8" stroke="#7F6F4A" stroke-width="2"/>
    </symbol>""",
}

_SMALL_MOLECULES: dict[str, str] = {
    "ion": """<symbol id="ion" viewBox="0 0 30 30" overflow="visible">
        <circle cx="15" cy="15" r="13"
              fill="#D4B8E2" stroke="#7F4A9C" stroke-width="1.5"/>
    </symbol>""",
    "atp": """<symbol id="atp" viewBox="0 0 80 30" overflow="visible">
        <polygon points="5,15 13,5 25,5 33,15 25,25 13,25"
              fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="48" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="60" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="72" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="33" y1="15" x2="42" y2="15" stroke="#C8901F" stroke-width="1.5"/>
    </symbol>""",
    "adp": """<symbol id="adp" viewBox="0 0 70 30" overflow="visible">
        <polygon points="5,15 13,5 25,5 33,15 25,25 13,25"
              fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="48" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="60" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="33" y1="15" x2="42" y2="15" stroke="#C8901F" stroke-width="1.5"/>
    </symbol>""",
    "camp": """<symbol id="camp" viewBox="0 0 50 32" overflow="visible">
        <polygon points="5,18 12,8 24,8 31,18 24,28 12,28"
              fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="40" cy="18" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="31" y1="18" x2="34" y2="18" stroke="#C8901F" stroke-width="1.5"/>
        <path d="M 18 8 Q 18 2 25 2 Q 32 2 32 8" fill="none" stroke="#C8901F" stroke-width="1.5"/>
    </symbol>""",
    "ip3": """<symbol id="ip3" viewBox="0 0 40 40" overflow="visible">
        <circle cx="20" cy="20" r="14"
              fill="#E8C5D4" stroke="#9C4A6F" stroke-width="1.5"/>
        <circle cx="10" cy="10" r="3" fill="#9C4A6F"/>
        <circle cx="30" cy="10" r="3" fill="#9C4A6F"/>
        <circle cx="20" cy="33" r="3" fill="#9C4A6F"/>
    </symbol>""",
    "dag": """<symbol id="dag" viewBox="0 0 50 40" overflow="visible">
        <rect x="5" y="15" width="13" height="10" rx="2"
              fill="#FFD4B0" stroke="#C86B1F" stroke-width="1.5"/>
        <path d="M 18 18 L 26 12 L 34 18 L 42 12"
              fill="none" stroke="#C86B1F" stroke-width="1.5"/>
        <path d="M 18 22 L 26 28 L 34 22 L 42 28"
              fill="none" stroke="#C86B1F" stroke-width="1.5"/>
    </symbol>""",
}

_MODIFICATIONS: dict[str, str] = {
    "p_badge": """<symbol id="p_badge" viewBox="0 0 24 24" overflow="visible">
        <circle cx="12" cy="12" r="10"
              fill="#FF6B47" stroke="#A33020" stroke-width="1.5"/>
        <text x="12" y="16" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif"
              font-size="12" fill="white" font-weight="bold">P</text>
    </symbol>""",
    "ub_badge": """<symbol id="ub_badge" viewBox="0 0 28 24" overflow="visible">
        <circle cx="14" cy="12" r="10"
              fill="#9C4ACC" stroke="#5A2A7C" stroke-width="1.5"/>
        <text x="14" y="16" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif"
              font-size="9" fill="white" font-weight="bold">Ub</text>
    </symbol>""",
    "ac_badge": """<symbol id="ac_badge" viewBox="0 0 28 24" overflow="visible">
        <circle cx="14" cy="12" r="10"
              fill="#5AB85A" stroke="#2A722A" stroke-width="1.5"/>
        <text x="14" y="16" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif"
              font-size="9" fill="white" font-weight="bold">Ac</text>
    </symbol>""",
}

_ORGANELLES: dict[str, str] = {
    "nucleus": """<symbol id="nucleus" viewBox="0 0 200 150" overflow="visible">
        <ellipse cx="100" cy="75" rx="92" ry="65"
              fill="#F0E0F0" stroke="#5A2A7C" stroke-width="2.5"/>
        <ellipse cx="100" cy="75" rx="86" ry="60"
              fill="none" stroke="#5A2A7C" stroke-width="1" opacity="0.6"/>
        <circle cx="20" cy="60" r="3" fill="#5A2A7C"/>
        <circle cx="180" cy="65" r="3" fill="#5A2A7C"/>
        <circle cx="100" cy="12" r="3" fill="#5A2A7C"/>
        <circle cx="100" cy="138" r="3" fill="#5A2A7C"/>
    </symbol>""",
    "mitochondrion": """<symbol id="mitochondrion" viewBox="0 0 150 80" overflow="visible">
        <ellipse cx="75" cy="40" rx="70" ry="35"
              fill="#F5D4C5" stroke="#8B4A2A" stroke-width="2.5"/>
        <path d="M 30 26 Q 40 36 50 26 Q 60 16 70 26"
              fill="none" stroke="#8B4A2A" stroke-width="1.5"/>
        <path d="M 30 54 Q 40 44 50 54 Q 60 64 70 54"
              fill="none" stroke="#8B4A2A" stroke-width="1.5"/>
        <path d="M 80 26 Q 90 36 100 26 Q 110 16 120 26"
              fill="none" stroke="#8B4A2A" stroke-width="1.5"/>
        <path d="M 80 54 Q 90 44 100 54 Q 110 64 120 54"
              fill="none" stroke="#8B4A2A" stroke-width="1.5"/>
    </symbol>""",
    "er_compartment": """<symbol id="er_compartment" viewBox="0 0 200 120" overflow="visible">
        <path d="M 10 30 Q 50 12 90 30 T 190 30 L 190 90 Q 150 108 110 90 T 10 90 Z"
              fill="#F5E8D0" stroke="#8B6F35" stroke-width="2"/>
    </symbol>""",
    "golgi": """<symbol id="golgi" viewBox="0 0 120 80" overflow="visible">
        <path d="M 10 20 Q 60 10 110 20" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
        <path d="M 12 32 Q 60 24 108 32" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
        <path d="M 14 44 Q 60 38 106 44" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
        <path d="M 16 56 Q 60 52 104 56" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
        <path d="M 18 68 Q 60 66 102 68" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
    </symbol>""",
}

_STRUCTURAL: dict[str, str] = {
    "lipid_bilayer": """<symbol id="lipid_bilayer" viewBox="0 0 100 24" overflow="visible" preserveAspectRatio="xMidYMid meet">
        <circle cx="10" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="25" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="40" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="55" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="70" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="85" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <line x1="10" y1="10" x2="10" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="25" y1="10" x2="25" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="40" y1="10" x2="40" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="55" y1="10" x2="55" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="70" y1="10" x2="70" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="85" y1="10" x2="85" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="10" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="25" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="40" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="55" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="70" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="85" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
    </symbol>""",
}


_GENERAL: dict[str, str] = {
    "microscope": """<symbol id="microscope" viewBox="0 0 40 60" overflow="visible">
        <rect x="6" y="50" width="28" height="6" rx="2" fill="#5A6B7F" stroke="#2A3F55" stroke-width="1.5"/>
        <rect x="16" y="22" width="8" height="30" fill="#5A6B7F" stroke="#2A3F55" stroke-width="1.5"/>
        <rect x="10" y="42" width="20" height="3" fill="#2A3F55"/>
        <rect x="17" y="36" width="6" height="6" fill="#A8C5E2" stroke="#2A3F55" stroke-width="1.5"/>
        <line x1="20" y1="22" x2="14" y2="10" stroke="#2A3F55" stroke-width="3" stroke-linecap="round"/>
        <circle cx="14" cy="10" r="3.5" fill="#A8C5E2" stroke="#2A3F55" stroke-width="1.5"/>
    </symbol>""",
    "lab_flask": """<symbol id="lab_flask" viewBox="0 0 40 50" overflow="visible">
        <rect x="17" y="5" width="6" height="10" fill="#E5E5E5" stroke="#4A7A3F" stroke-width="1.5"/>
        <path d="M 17 15 L 6 42 Q 20 50 34 42 L 23 15 Z"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="1.5"/>
        <line x1="11" y1="35" x2="29" y2="35" stroke="#4A7A3F" stroke-width="1" stroke-dasharray="2,2"/>
        <circle cx="14" cy="40" r="1.5" fill="#4A7A3F" opacity="0.5"/>
        <circle cx="22" cy="38" r="1.2" fill="#4A7A3F" opacity="0.5"/>
    </symbol>""",
    "pill_capsule": """<symbol id="pill_capsule" viewBox="0 0 60 25" overflow="visible">
        <path d="M 30 5 L 11 5 Q 3 5 3 12.5 Q 3 20 11 20 L 30 20 Z"
              fill="#FFE0B0" stroke="#9C5F2A" stroke-width="1.5"/>
        <path d="M 30 5 L 49 5 Q 57 5 57 12.5 Q 57 20 49 20 L 30 20 Z"
              fill="#FFB570" stroke="#9C5F2A" stroke-width="1.5"/>
    </symbol>""",
    "patient_silhouette": """<symbol id="patient_silhouette" viewBox="0 0 40 55" overflow="visible">
        <circle cx="20" cy="14" r="9" fill="#E8C5B5" stroke="#9C5F47" stroke-width="1.5"/>
        <path d="M 5 50 L 8 32 Q 12 25 20 25 Q 28 25 32 32 L 35 50 Z"
              fill="#E8C5B5" stroke="#9C5F47" stroke-width="1.5"/>
    </symbol>""",
    "document_stamp": """<symbol id="document_stamp" viewBox="0 0 45 50" overflow="visible">
        <path d="M 5 5 L 32 5 L 40 13 L 40 45 L 5 45 Z"
              fill="#FFFFFF" stroke="#444444" stroke-width="1.5"/>
        <path d="M 32 5 L 32 13 L 40 13 Z" fill="#DDDDDD" stroke="#444444" stroke-width="1.5"/>
        <line x1="10" y1="20" x2="35" y2="20" stroke="#888888" stroke-width="1"/>
        <line x1="10" y1="25" x2="35" y2="25" stroke="#888888" stroke-width="1"/>
        <line x1="10" y1="30" x2="30" y2="30" stroke="#888888" stroke-width="1"/>
        <circle cx="32" cy="38" r="7" fill="none" stroke="#D03020" stroke-width="2"/>
        <path d="M 28 38 L 31 41 L 36 35" fill="none" stroke="#D03020" stroke-width="2" stroke-linecap="round"/>
    </symbol>""",
    "chart_graph": """<symbol id="chart_graph" viewBox="0 0 50 40" overflow="visible">
        <line x1="6" y1="5" x2="6" y2="35" stroke="#444444" stroke-width="1.5"/>
        <line x1="6" y1="35" x2="46" y2="35" stroke="#444444" stroke-width="1.5"/>
        <rect x="10" y="25" width="6" height="10" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1"/>
        <rect x="20" y="18" width="6" height="17" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1"/>
        <rect x="30" y="12" width="6" height="23" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1"/>
        <rect x="40" y="8" width="6" height="27" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1"/>
        <path d="M 13 23 L 23 16 L 33 10 L 43 6" fill="none" stroke="#D03020" stroke-width="1.5"/>
    </symbol>""",
    "milestone_marker": """<symbol id="milestone_marker" viewBox="0 0 30 40" overflow="visible">
        <line x1="6" y1="5" x2="6" y2="38" stroke="#444444" stroke-width="2"/>
        <ellipse cx="6" cy="38" rx="4" ry="1.5" fill="#444444"/>
        <path d="M 6 6 L 26 11 L 6 16 Z" fill="#FF8847" stroke="#9C4A20" stroke-width="1.5"/>
    </symbol>""",
    "gear": """<symbol id="gear" viewBox="0 0 40 40" overflow="visible">
        <g fill="#D4D4D4" stroke="#666666" stroke-width="1.5">
            <rect x="18" y="2" width="4" height="6"/>
            <rect x="18" y="32" width="4" height="6"/>
            <rect x="2" y="18" width="6" height="4"/>
            <rect x="32" y="18" width="6" height="4"/>
        </g>
        <circle cx="20" cy="20" r="11" fill="#D4D4D4" stroke="#666666" stroke-width="1.5"/>
        <circle cx="20" cy="20" r="4" fill="#FFFFFF" stroke="#666666" stroke-width="1.5"/>
    </symbol>""",
    "clock": """<symbol id="clock" viewBox="0 0 40 40" overflow="visible">
        <circle cx="20" cy="20" r="17" fill="#F5F5F5" stroke="#444444" stroke-width="2"/>
        <line x1="20" y1="5" x2="20" y2="9" stroke="#444444" stroke-width="1.5"/>
        <line x1="35" y1="20" x2="31" y2="20" stroke="#444444" stroke-width="1.5"/>
        <line x1="20" y1="35" x2="20" y2="31" stroke="#444444" stroke-width="1.5"/>
        <line x1="5" y1="20" x2="9" y2="20" stroke="#444444" stroke-width="1.5"/>
        <line x1="20" y1="20" x2="20" y2="11" stroke="#222222" stroke-width="2" stroke-linecap="round"/>
        <line x1="20" y1="20" x2="27" y2="20" stroke="#222222" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="20" cy="20" r="1.5" fill="#222222"/>
    </symbol>""",
    "magnifying_glass": """<symbol id="magnifying_glass" viewBox="0 0 40 40" overflow="visible">
        <circle cx="16" cy="16" r="11" fill="#FFFFFF" stroke="#3A5F7F" stroke-width="2.5"/>
        <circle cx="16" cy="16" r="9" fill="#A8C5E2" opacity="0.3"/>
        <line x1="24" y1="24" x2="36" y2="36" stroke="#3A5F7F" stroke-width="3" stroke-linecap="round"/>
    </symbol>""",
}


SYMBOLS: dict[str, str] = {
    **_RECEPTORS,
    **_ENZYMES,
    **_SMALL_MOLECULES,
    **_MODIFICATIONS,
    **_ORGANELLES,
    **_STRUCTURAL,
    **_GENERAL,
}


CATALOG: list[SymbolEntry] = [
    # Receptors / membrane proteins
    SymbolEntry("gpcr", "GPCR", "receptor",
                "G-protein-coupled / 7-transmembrane receptors. Examples: AT1R, β-adrenergic, rhodopsin.",
                60, 80),
    SymbolEntry("rtk", "RTK", "receptor",
                "Receptor tyrosine kinases with extracellular ligand-binding + intracellular kinase domain. Examples: EGFR, insulin receptor.",
                60, 100),
    SymbolEntry("ion_channel", "Ion channel", "receptor",
                "Membrane ion channels (voltage-gated, ligand-gated, leak). Pore visible between two subunits.",
                60, 80),
    SymbolEntry("transporter", "Transporter", "receptor",
                "Active or facilitated transporters. Arrow inside indicates direction.",
                60, 80),
    SymbolEntry("generic_membrane_protein", "Generic membrane protein", "receptor",
                "Membrane protein that doesn't fit a more specific category.",
                60, 80),
    # Cytosolic enzymes
    SymbolEntry("kinase", "Kinase", "enzyme",
                "Cytosolic kinase enzymes. Examples: PKA, PKC, MAPK, Akt.",
                80, 50),
    SymbolEntry("phosphatase", "Phosphatase", "enzyme",
                "Cytosolic phosphatases. Examples: PP2A, PTP.",
                80, 50),
    SymbolEntry("generic_protein", "Generic protein", "enzyme",
                "Cytosolic protein that doesn't fit a more specific category.",
                80, 50),
    SymbolEntry("complex", "Protein complex", "enzyme",
                "Multi-subunit cytosolic complex. Examples: G-protein heterotrimer, RISC, ribosome.",
                110, 60),
    # Small molecules / ions
    SymbolEntry("ion", "Ion / charge carrier", "small_molecule",
                "Generic small ion or charged molecule. Add an adjacent <text> for the species (Ca²⁺, Na⁺, K⁺, H⁺, Cl⁻, Mg²⁺).",
                30, 30),
    SymbolEntry("atp", "ATP", "small_molecule",
                "Adenosine triphosphate. Hexagon (adenosine) + 3 circles (phosphates).",
                80, 30),
    SymbolEntry("adp", "ADP", "small_molecule",
                "Adenosine diphosphate. Hexagon + 2 circles.",
                70, 30),
    SymbolEntry("camp", "cAMP", "small_molecule",
                "Cyclic AMP. Hexagon with cyclic notation + 1 phosphate.",
                50, 32),
    SymbolEntry("ip3", "IP₃", "small_molecule",
                "Inositol 1,4,5-trisphosphate. Circle with 3 phosphate marks.",
                40, 40),
    SymbolEntry("dag", "DAG", "small_molecule",
                "Diacylglycerol. Glycerol head + 2 fatty acid tails.",
                50, 40),
    # Modifications
    SymbolEntry("p_badge", "Phosphorylation badge", "modification",
                "Small red 'P' badge. Place near the modified residue or protein.",
                24, 24),
    SymbolEntry("ub_badge", "Ubiquitin badge", "modification",
                "Small purple 'Ub' badge.",
                28, 24),
    SymbolEntry("ac_badge", "Acetylation badge", "modification",
                "Small green 'Ac' badge.",
                28, 24),
    # Organelles
    SymbolEntry("nucleus", "Nucleus", "organelle",
                "Cell nucleus with double membrane and nuclear pores.",
                200, 150),
    SymbolEntry("mitochondrion", "Mitochondrion", "organelle",
                "Mitochondrion with cristae.",
                150, 80),
    SymbolEntry("er_compartment", "Endoplasmic reticulum", "organelle",
                "ER cisterna / sheet. Use for IP₃R-bearing intracellular Ca²⁺ store.",
                200, 120),
    SymbolEntry("golgi", "Golgi apparatus", "organelle",
                "Stacked Golgi cisternae.",
                120, 80),
    # Structural
    SymbolEntry("lipid_bilayer", "Lipid bilayer", "structural",
                "Tileable membrane fragment. Use multiple <use> with adjacent x-positions to build a long membrane.",
                100, 24),
    # General schematic — useful for abstract pipelines, workflows, frameworks
    SymbolEntry("microscope", "Microscope", "general",
                "Research / discovery / basic-science stage. Place inside Discovery / Research stage boxes.",
                40, 60),
    SymbolEntry("lab_flask", "Lab flask", "general",
                "Lab work / preclinical / wet-bench stage. Erlenmeyer flask with liquid.",
                40, 50),
    SymbolEntry("pill_capsule", "Pill / drug capsule", "general",
                "Pharmaceutical / drug / therapeutic. Capsule shape, two-tone.",
                60, 25),
    SymbolEntry("patient_silhouette", "Patient / human subject", "general",
                "Clinical trial / human-subject / patient stage. Head + shoulders silhouette.",
                40, 55),
    SymbolEntry("document_stamp", "Approved document", "general",
                "Regulatory approval / FDA / paperwork stage. Document with red checkmark stamp.",
                45, 50),
    SymbolEntry("chart_graph", "Chart / analytics", "general",
                "Analytics / surveillance / data-monitoring stage. Bar chart with trend line.",
                50, 40),
    SymbolEntry("milestone_marker", "Milestone flag", "general",
                "Timeline waypoint / milestone. Orange flag on pole.",
                30, 40),
    SymbolEntry("gear", "Gear / process", "general",
                "Process / mechanism / operations. Mechanical gear.",
                40, 40),
    SymbolEntry("clock", "Clock / time", "general",
                "Time / duration / scheduling.",
                40, 40),
    SymbolEntry("magnifying_glass", "Magnifying glass / analysis", "general",
                "Analysis / inspection / discovery. Lens with handle.",
                40, 40),
]


def build_defs_block() -> str:
    """Return a `<defs>...</defs>` block containing every symbol."""
    return "<defs>\n" + "\n".join(SYMBOLS.values()) + "\n</defs>"


def build_catalog_for_prompt() -> str:
    """Return a markdown-bullet catalog suitable for inclusion in the system prompt."""
    by_cat: dict[str, list[SymbolEntry]] = {}
    for entry in CATALOG:
        by_cat.setdefault(entry.category, []).append(entry)

    order = [
        "receptor", "enzyme", "small_molecule", "modification",
        "organelle", "structural", "general",
    ]
    titles = {
        "receptor": "Receptors / membrane proteins",
        "enzyme": "Cytosolic enzymes / proteins",
        "small_molecule": "Ions and small molecules",
        "modification": "Post-translational modifications",
        "organelle": "Organelles",
        "structural": "Structural elements",
        "general": "General schematic (workflows, pipelines, timelines)",
    }
    lines: list[str] = []
    for cat in order:
        if cat not in by_cat:
            continue
        lines.append(f"\n**{titles[cat]}**")
        for e in by_cat[cat]:
            lines.append(
                f"- `{e.id}` ({e.name}, {e.default_w}×{e.default_h}): {e.use_when}"
            )
    return "\n".join(lines).strip()
