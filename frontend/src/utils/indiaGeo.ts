/**
 * India Geographic Data — States grouped by Scope 3 region,
 * major cities per state, and representative pincodes.
 * Pincode verification done via postalpincode.in free API.
 */

export const REGION_STATES: Record<string, { name: string; states: string[] }> = {
  north: {
    name: 'North India',
    states: ['Delhi', 'Haryana', 'Himachal Pradesh', 'Jammu & Kashmir',
             'Ladakh', 'Punjab', 'Rajasthan', 'Uttar Pradesh', 'Uttarakhand'],
  },
  south: {
    name: 'South India',
    states: ['Andhra Pradesh', 'Karnataka', 'Kerala', 'Puducherry',
             'Tamil Nadu', 'Telangana'],
  },
  east: {
    name: 'East India',
    states: ['Arunachal Pradesh', 'Assam', 'Bihar', 'Jharkhand', 'Manipur',
             'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Sikkim',
             'Tripura', 'West Bengal'],
  },
  west: {
    name: 'West India',
    states: ['Dadra & Nagar Haveli and Daman & Diu', 'Goa', 'Gujarat', 'Maharashtra'],
  },
  central: {
    name: 'Central India',
    states: ['Chhattisgarh', 'Madhya Pradesh'],
  },
}

export const STATE_CITIES: Record<string, string[]> = {
  'Delhi':              ['New Delhi', 'Dwarka', 'Rohini', 'Shahdara', 'Janakpuri'],
  'Haryana':            ['Gurugram', 'Faridabad', 'Panipat', 'Ambala', 'Hisar', 'Karnal', 'Sonipat'],
  'Himachal Pradesh':   ['Shimla', 'Dharamsala', 'Manali', 'Solan', 'Mandi'],
  'Jammu & Kashmir':    ['Srinagar', 'Jammu', 'Anantnag', 'Baramulla'],
  'Ladakh':             ['Leh', 'Kargil'],
  'Punjab':             ['Ludhiana', 'Amritsar', 'Jalandhar', 'Patiala', 'Mohali', 'Bathinda'],
  'Rajasthan':          ['Jaipur', 'Jodhpur', 'Udaipur', 'Kota', 'Ajmer', 'Bikaner', 'Alwar'],
  'Uttar Pradesh':      ['Lucknow', 'Kanpur', 'Agra', 'Varanasi', 'Prayagraj', 'Meerut', 'Noida', 'Ghaziabad'],
  'Uttarakhand':        ['Dehradun', 'Haridwar', 'Rishikesh', 'Nainital', 'Roorkee'],
  'Andhra Pradesh':     ['Visakhapatnam', 'Vijayawada', 'Guntur', 'Tirupati', 'Nellore', 'Kurnool'],
  'Karnataka':          ['Bengaluru', 'Mysuru', 'Hubli', 'Mangaluru', 'Belagavi', 'Davangere'],
  'Kerala':             ['Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Thrissur', 'Kollam', 'Kannur'],
  'Puducherry':         ['Puducherry', 'Karaikal', 'Mahe'],
  'Tamil Nadu':         ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem', 'Tirunelveli', 'Vellore'],
  'Telangana':          ['Hyderabad', 'Warangal', 'Karimnagar', 'Nizamabad', 'Khammam'],
  'Arunachal Pradesh':  ['Itanagar', 'Naharlagun', 'Pasighat'],
  'Assam':              ['Guwahati', 'Dibrugarh', 'Silchar', 'Jorhat', 'Nagaon'],
  'Bihar':              ['Patna', 'Gaya', 'Bhagalpur', 'Muzaffarpur', 'Darbhanga'],
  'Jharkhand':          ['Ranchi', 'Jamshedpur', 'Dhanbad', 'Bokaro', 'Deoghar'],
  'Manipur':            ['Imphal', 'Churachandpur'],
  'Meghalaya':          ['Shillong', 'Tura'],
  'Mizoram':            ['Aizawl', 'Lunglei'],
  'Nagaland':           ['Kohima', 'Dimapur'],
  'Odisha':             ['Bhubaneswar', 'Cuttack', 'Rourkela', 'Berhampur', 'Sambalpur'],
  'Sikkim':             ['Gangtok', 'Namchi'],
  'Tripura':            ['Agartala', 'Udaipur'],
  'West Bengal':        ['Kolkata', 'Howrah', 'Durgapur', 'Asansol', 'Siliguri', 'Kharagpur'],
  'Dadra & Nagar Haveli and Daman & Diu': ['Daman', 'Diu', 'Silvassa'],
  'Goa':                ['Panaji', 'Margao', 'Vasco da Gama', 'Mapusa'],
  'Gujarat':            ['Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Gandhinagar', 'Bhavnagar', 'Jamnagar'],
  'Maharashtra':        ['Mumbai', 'Pune', 'Nagpur', 'Nashik', 'Aurangabad', 'Thane', 'Solapur', 'Kolhapur'],
  'Chhattisgarh':       ['Raipur', 'Bhilai', 'Bilaspur', 'Durg', 'Korba'],
  'Madhya Pradesh':     ['Bhopal', 'Indore', 'Jabalpur', 'Gwalior', 'Ujjain', 'Rewa'],
}

// Representative pincodes (one per city — user can override)
export const CITY_PINCODE: Record<string, string> = {
  'New Delhi': '110001', 'Dwarka': '110075', 'Rohini': '110085',
  'Gurugram': '122001', 'Faridabad': '121001', 'Panipat': '132103',
  'Shimla': '171001', 'Dharamsala': '176215',
  'Srinagar': '190001', 'Jammu': '180001',
  'Leh': '194101',
  'Ludhiana': '141001', 'Amritsar': '143001', 'Jalandhar': '144001', 'Patiala': '147001', 'Mohali': '160062',
  'Jaipur': '302001', 'Jodhpur': '342001', 'Udaipur': '313001', 'Kota': '324001', 'Ajmer': '305001',
  'Lucknow': '226001', 'Kanpur': '208001', 'Agra': '282001', 'Varanasi': '221001',
  'Noida': '201301', 'Ghaziabad': '201001', 'Prayagraj': '211001', 'Meerut': '250001',
  'Dehradun': '248001', 'Haridwar': '249401', 'Rishikesh': '249201',
  'Visakhapatnam': '530001', 'Vijayawada': '520001', 'Guntur': '522001', 'Tirupati': '517501',
  'Bengaluru': '560001', 'Mysuru': '570001', 'Hubli': '580020', 'Mangaluru': '575001',
  'Thiruvananthapuram': '695001', 'Kochi': '682001', 'Kozhikode': '673001', 'Thrissur': '680001',
  'Puducherry': '605001',
  'Chennai': '600001', 'Coimbatore': '641001', 'Madurai': '625001', 'Tiruchirappalli': '620001',
  'Hyderabad': '500001', 'Warangal': '506001', 'Karimnagar': '505001',
  'Guwahati': '781001', 'Dibrugarh': '786001', 'Silchar': '788001',
  'Patna': '800001', 'Gaya': '823001', 'Bhagalpur': '812001',
  'Ranchi': '834001', 'Jamshedpur': '831001', 'Dhanbad': '826001',
  'Imphal': '795001',
  'Shillong': '793001',
  'Aizawl': '796001',
  'Kohima': '797001', 'Dimapur': '797112',
  'Bhubaneswar': '751001', 'Cuttack': '753001', 'Rourkela': '769001',
  'Gangtok': '737101',
  'Agartala': '799001',
  'Kolkata': '700001', 'Howrah': '711101', 'Durgapur': '713201', 'Siliguri': '734001',
  'Daman': '396210', 'Silvassa': '396230',
  'Panaji': '403001', 'Margao': '403601',
  'Ahmedabad': '380001', 'Surat': '395001', 'Vadodara': '390001', 'Rajkot': '360001',
  'Gandhinagar': '382010', 'Bhavnagar': '364001',
  'Mumbai': '400001', 'Pune': '411001', 'Nagpur': '440001', 'Nashik': '422001',
  'Thane': '400601', 'Aurangabad': '431001',
  'Raipur': '492001', 'Bhilai': '490001', 'Bilaspur': '495001',
  'Bhopal': '462001', 'Indore': '452001', 'Jabalpur': '482001', 'Gwalior': '474001',
}

export async function verifyPincode(pincode: string): Promise<{
  valid: boolean; city?: string; state?: string; error?: string
}> {
  if (!/^\d{6}$/.test(pincode)) {
    return { valid: false, error: 'Pincode must be exactly 6 digits' }
  }
  try {
    const res = await fetch(`https://api.postalpincode.in/pincode/${pincode}`)
    const data = await res.json()
    if (data[0]?.Status === 'Success' && data[0]?.PostOffice?.length > 0) {
      const po = data[0].PostOffice[0]
      return { valid: true, city: po.District, state: po.State }
    }
    return { valid: false, error: 'Pincode not found in India Post database' }
  } catch {
    return { valid: true } // If API fails, allow it — don't block the user
  }
}

export function getStatesForRegion(region: string): string[] {
  return REGION_STATES[region]?.states || Object.values(REGION_STATES).flatMap(r => r.states)
}

export function getCitiesForState(state: string): string[] {
  return STATE_CITIES[state] || []
}

export function getPincodeForCity(city: string): string {
  return CITY_PINCODE[city] || ''
}
