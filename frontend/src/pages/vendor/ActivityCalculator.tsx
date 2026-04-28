import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Calculator, ChevronDown, ChevronRight } from 'lucide-react'
import { SectionHeader } from '@/components/ui'
import HelpTooltip from '@/components/ui/HelpTooltip'
import { SCOPE3_CATEGORIES } from '@/utils/constants'

const CATEGORY_GUIDES: Record<number, {
  name: string
  what: string
  formula: string
  inputs: { label: string; unit: string; example: string; help: string }[]
  tips: string[]
  references: string[]
}> = {
  1: {
    name: 'Purchased Goods & Services',
    what: 'The weight of raw materials, components, or finished goods you supply to the company.',
    formula: 'Activity Value = Total weight of goods supplied in the period',
    inputs: [
      {
        label: 'Weight of goods', unit: 'tonnes or kg', example: '500 tonnes of steel sheets',
        help: 'Use delivery notes, purchase orders, or weigh-bridge receipts. Convert kg to tonnes (÷1000).'
      },
      {
        label: 'Spend (if weight unknown)', unit: 'INR', example: '₹50,00,000',
        help: 'Use invoices. Spend-based gives a lower data quality grade (C).'
      },
    ],
    tips: [
      'Use weigh-bridge certificates for highest accuracy (Grade A)',
      'Group by material type — different materials have very different EFs',
      'Packaging weight should be excluded unless it becomes waste at buyer',
    ],
    references: ['DEFRA 2024 Table 1 — Material EFs', 'GHG Protocol Category 1 Guidance'],
  },
  4: {
    name: 'Upstream Transport & Distribution',
    what: 'The freight movement involved in delivering your goods to the company.',
    formula: 'Activity Value = Distance (km) × Weight transported (tonnes) = tonne-km',
    inputs: [
      {
        label: 'Distance', unit: 'km', example: '250 km (Mumbai to Pune)',
        help: 'Use Google Maps or logistics provider records. For sea/rail, use actual route distance.'
      },
      {
        label: 'Cargo weight', unit: 'tonnes', example: '10 tonnes per shipment',
        help: 'Use delivery note or truck capacity × load factor. Average truck load factor = 60-70%.'
      },
    ],
    tips: [
      'Tonne-km = Distance × Cargo weight (multiply both)',
      'Sum across all deliveries in the reporting period',
      'If returning empty, count only laden (loaded) trips',
      'Air freight has ~10× higher EF than road — report separately',
    ],
    references: ['DEFRA 2024 Table 7 — Freight Transport EFs'],
  },
  5: {
    name: 'Waste Generated in Operations',
    what: 'The weight of waste you generate in your operations and its disposal method.',
    formula: 'Activity Value = Weight of waste by disposal type (landfill / incineration / recycled)',
    inputs: [
      {
        label: 'Waste to landfill', unit: 'tonnes', example: '50 tonnes mixed waste',
        help: 'Use waste contractor certificates or weighbridge records.'
      },
      {
        label: 'Waste incinerated', unit: 'tonnes', example: '10 tonnes hazardous waste',
        help: 'Requires incineration plant certificates.'
      },
      {
        label: 'Waste recycled', unit: 'tonnes', example: '30 tonnes metal scrap',
        help: 'Get recycling certificates from authorised recyclers.'
      },
    ],
    tips: [
      'Submit separate records for each waste stream',
      'Recycling has a much lower EF than landfill',
      'Hazardous waste should use specific EFs — contact your manager',
      'Municipal solid waste = landfill EF',
    ],
    references: ['DEFRA 2024 Table 5 — Waste EFs', 'PCB Guidelines India'],
  },
  6: {
    name: 'Business Travel',
    what: 'Distance travelled by employees for business purposes.',
    formula: 'Activity Value = Total distance per travel mode (km)',
    inputs: [
      {
        label: 'Air travel distance', unit: 'passenger-km', example: '5,000 km (Delhi–Mumbai–Delhi × 2 people)',
        help: 'Multiply route distance × number of passengers. Use flight booking records.'
      },
      {
        label: 'Rail distance', unit: 'passenger-km', example: '800 km',
        help: 'From IRCTC booking records. Multiply km × travellers.'
      },
      {
        label: 'Car distance', unit: 'vehicle-km', example: '2,000 km',
        help: 'From fuel claims, cab bills, or GPS records. This is vehicle-km not passenger-km.'
      },
      {
        label: 'Hotel nights', unit: 'nights', example: '15 nights',
        help: 'From hotel bills or employee expense claims.'
      },
    ],
    tips: [
      'Submit separate records for each mode of transport',
      'Domestic flights: use Delhi-Mumbai (~1400 km) as reference',
      'WFH days reduce commuting — track separately (Category 7)',
      'Business class flights have a higher radiative forcing multiplier',
    ],
    references: ['DEFRA 2024 Table 6 — Travel EFs', 'ICAO Carbon Calculator'],
  },
  7: {
    name: 'Employee Commuting',
    what: 'Distance employees travel between home and workplace.',
    formula: 'Activity Value = Avg commute distance × working days × employees × mode split',
    inputs: [
      {
        label: 'Employee count', unit: 'persons', example: '120 employees',
        help: 'Average headcount for the period.'
      },
      {
        label: 'Working days', unit: 'days', example: '240 days/year',
        help: 'Subtract weekends, holidays, WFH days.'
      },
      {
        label: 'Avg one-way commute', unit: 'km', example: '12 km',
        help: 'Use employee survey or HR records. Include both directions.'
      },
    ],
    tips: [
      'Calculate: Employees × Working days × 2 (both ways) × avg km = total passenger-km',
      'Use employee travel survey for mode split (car/bus/metro)',
      'WFH days = zero emissions — track and subtract',
      'Company-provided bus = lower EF than private car',
    ],
    references: ['DEFRA 2024 Table 6 — Commuting', 'GHG Protocol Cat 7 Guidance'],
  },
}

const CATEGORY_QUICK: Record<number, { unit: string; efNote: string }> = {
  2: { unit: 'tonnes (weight of capital goods)', efNote: 'EF varies by asset type (machinery, buildings, vehicles)' },
  3: { unit: 'kWh (electricity) or litres (fuel)', efNote: 'India grid = 0.82 kgCO₂e/kWh' },
  8: { unit: 'tonne-km (same as upstream transport)', efNote: 'Use customer-facing delivery records' },
  9: { unit: 'kWh (energy used in processing)', efNote: 'Requires downstream processing energy data' },
  10: { unit: 'units sold × lifetime energy use (kWh)', efNote: 'Requires product specification sheets' },
  11: { unit: 'tonnes (product weight at end-of-life)', efNote: 'By disposal method (landfill/recycle)' },
  12: { unit: 'kWh (energy consumed by leased asset)', efNote: 'From energy bills of leased properties' },
  13: { unit: 'INR (franchise revenue)', efNote: 'Spend-based — use franchise revenue figures' },
  14: { unit: 'INR (investment value)', efNote: 'PCAF method — use EVIC of investee company' },
  15: { unit: 'As defined by your category', efNote: 'Contact your manager for custom EF guidance' },
}

export default function ActivityCalculator() {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<number | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)

  return (
    <div>
      <SectionHeader
        title="Activity Value Calculator"
        description="Step-by-step guidance on measuring your emission activity data for each Scope 3 category"
        action={
          <button onClick={() => navigate('/submit')} className="btn-secondary">
            <ArrowLeft size={14} /> Back to Submit
          </button>
        }
      />

      {/* Intro */}
      <div className="card p-5 mb-5 bg-brand-50 border-brand-100">
        <div className="flex items-start gap-3">
          <Calculator size={20} className="text-brand-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-brand-900 mb-1">What is Activity Value?</h3>
            <p className="text-sm text-brand-800 leading-relaxed">
              The Activity Value is the measurable quantity of an activity that causes greenhouse gas
              emissions — such as tonnes of material, kilometres travelled, or kilowatt-hours of energy.
              Emissions are calculated as: <code className="bg-brand-100 px-1 rounded">CO₂e = Activity Value × Emission Factor</code>
            </p>
          </div>
        </div>
      </div>

      {/* Category selector */}
      <div className="grid grid-cols-1 gap-3">
        {Object.entries(CATEGORY_GUIDES).map(([id, guide]) => {
          const catId = parseInt(id)
          const isOpen = expanded === catId
          return (
            <div key={id} className="card overflow-hidden">
              <button
                onClick={() => setExpanded(isOpen ? null : catId)}
                className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-lg bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center flex-shrink-0">
                    {id}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{guide.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{guide.what}</p>
                  </div>
                </div>
                {isOpen ? <ChevronDown size={16} className="text-gray-400 flex-shrink-0" /> : <ChevronRight size={16} className="text-gray-400 flex-shrink-0" />}
              </button>

              {isOpen && (
                <div className="px-4 pb-5 border-t border-gray-100">
                  {/* Formula */}
                  <div className="mt-4 p-3 bg-gray-900 rounded-xl">
                    <p className="text-xs text-gray-400 mb-1 uppercase tracking-wide">Formula</p>
                    <code className="text-sm text-green-400 font-mono">{guide.formula}</code>
                  </div>

                  {/* Input fields guidance */}
                  <div className="mt-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">What to measure</p>
                    <div className="space-y-3">
                      {guide.inputs.map((inp, i) => (
                        <div key={i} className="p-3 bg-gray-50 rounded-xl">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-semibold text-gray-800">{inp.label}</span>
                            <span className="text-xs text-gray-400 bg-white border border-gray-200 px-1.5 py-0.5 rounded">{inp.unit}</span>
                          </div>
                          <p className="text-xs text-gray-600 leading-relaxed">{inp.help}</p>
                          <p className="text-xs text-brand-600 mt-1">📌 Example: {inp.example}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Tips */}
                  <div className="mt-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Tips</p>
                    <ul className="space-y-1.5">
                      {guide.tips.map((tip, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-gray-700">
                          <span className="text-brand-500 font-bold flex-shrink-0">→</span>
                          {tip}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* References */}
                  <div className="mt-4 pt-3 border-t border-gray-100">
                    <p className="text-xs text-gray-400">References: {guide.references.join(' · ')}</p>
                  </div>

                  <button onClick={() => navigate('/submit')}
                    className="btn-primary mt-4 text-sm">
                    Go to Submit Data →
                  </button>
                </div>
              )}
            </div>
          )
        })}

        {/* Other categories (quick reference) */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Other Categories — Quick Reference</h3>
          <div className="space-y-2">
            {Object.entries(CATEGORY_QUICK).map(([id, info]) => {
              return (
                <div key={id} className="flex items-start gap-3 p-2.5 bg-gray-50 rounded-lg text-xs">
                  <span className="w-6 h-6 rounded bg-white border border-gray-200 text-gray-600 font-bold flex items-center justify-center flex-shrink-0">{id}</span>
                  <div className="flex-1">
                    <p className="font-medium text-gray-800">{SCOPE3_CATEGORIES[parseInt(id)]}</p>
                    <p className="text-gray-500 mt-0.5">Unit: <span className="font-medium">{info.unit}</span></p>
                    <p className="text-gray-400">EF note: {info.efNote}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
