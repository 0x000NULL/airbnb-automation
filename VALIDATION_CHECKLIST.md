# Pre-Development Validation Checklist

Before building, validate these assumptions with real data & user interviews.

## 🎯 Market Validation

### Customer Pain Points
- [ ] Interview 20+ Airbnb hosts about their biggest operational pain
  - [ ] Focus on hosts with 3+ properties
  - [ ] Ask: "What's the most time-consuming task?"
  - [ ] Ask: "What would you pay to automate turnover?"
  - [ ] Ask: "Do you use cleaning services today?"
  
- [ ] Validate willingness to pay
  - [ ] "Would you pay 15% commission on turnover costs?"
  - [ ] "Would you pay $49/month SaaS fee?"
  - [ ] What's the actual turnover cost (cleaning, supplies, labor)?

### Market Size
- [ ] Research actual Airbnb host distribution
  - [ ] How many hosts manage 3+ properties?
  - [ ] Geographic concentration (US, EU, APAC)?
  - [ ] Average property size/booking frequency?

- [ ] Competitive analysis
  - [ ] What features does Vacasa offer?
  - [ ] Why don't hosts use Vacasa? (cost, control, availability?)
  - [ ] Are there niche competitors?

## 💰 Financial Validation

### Unit Economics
- [ ] What's the actual cost of turnover?
  - [ ] Cleaner rates (call local cleaning services)
  - [ ] Supplies (linens, toiletries, etc)
  - [ ] Time cost (host supervision)
  
- [ ] RentAHuman pricing
  - [ ] Get API access + pricing sheet
  - [ ] How much do cleaners charge?
  - [ ] Availability in key markets (Vegas, Miami, LA, NYC, Austin)?

- [ ] Your margin calculation
  - [ ] If turnover costs $200, can you offer at 15% commission?
  - [ ] Does that ($30 margin) scale to profitability?

### Revenue Projections
- [ ] Research host cohort data
  - [ ] How many Airbnb hosts actually manage multiple properties?
  - [ ] What's the average number of turnovers per month?
  - [ ] What's monthly turnover cost per property?

- [ ] Calculate TAM → SAM → SOM
  - [ ] TAM: Total addressable market (all hosts)
  - [ ] SAM: Serviceable available market (multi-property hosts)
  - [ ] SOM: Serviceable obtainable market (realistic Year 1)

## 🔧 Technical Validation

### Airbnb/VRBO Integration
- [ ] Research official APIs
  - [ ] Does Airbnb have a public API for bookings? (check docs)
  - [ ] Does VRBO have a public API? (check docs)
  - [ ] What are rate limits, auth requirements?
  - [ ] Fallback: Is Selenium scraping viable?

- [ ] Data access
  - [ ] Can we fetch guest names, dates, special requests?
  - [ ] Can we push notifications back to guests?
  - [ ] Privacy implications (guest data)?

### RentAHuman Integration
- [ ] Get API access
  - [ ] Request API key from RentAHuman
  - [ ] Understand pricing structure
  - [ ] Review rate limits, error handling

- [ ] Test basic flow
  - [ ] Can you search for cleaners in key markets?
  - [ ] What's the response time?
  - [ ] How much variance in pricing?

- [ ] Understand availability
  - [ ] How many cleaners in Vegas, Miami, NYC?
  - [ ] What's the booking success rate (% who confirm)?
  - [ ] What's the cancellation rate (% who cancel after booking)?

## 👥 Product Validation

### User Interviews (20+ hosts)
- [ ] "Walk me through your typical turnover process"
- [ ] "What's the hardest part?"
- [ ] "How much do you spend on cleaning per turnover?"
- [ ] "Would you trust an AI to book cleaners for you?"
- [ ] "Would you pay 15% of turnover costs?"
- [ ] "Would you use this if it existed?"
- [ ] "Who else might benefit?"

### Host Communities (find + engage)
- [ ] Reddit: r/Airbnb, r/BecomingAHost, r/HostTrading
- [ ] Facebook: "Airbnb hosts", "Superhost success", "VRBO management"
- [ ] Online forums: HostMyGuest, Airbnb Community Center
- [ ] Local: Airbnb host meetups in major cities

### Feature Validation
- [ ] Hosts care most about: cleaning, guest communication, or maintenance?
- [ ] Should it auto-book, or just recommend humans?
- [ ] Should system handle payment, or just coordination?
- [ ] What's the must-have MVP vs nice-to-have?

## 🚀 GTM Validation

### Positioning
- [ ] What's the core value prop? (time saved, cost reduction, quality)
- [ ] Who's the ideal first customer? (2-10 property hosts, specific regions)
- [ ] What's the unfair advantage? (RentAHuman integration)

### Channels
- [ ] Which acquisition channels work for hosts?
  - [ ] Organic search (what keywords?)
  - [ ] Content marketing (blogs, YouTube)
  - [ ] Communities (Reddit, Facebook)
  - [ ] Direct sales (outreach to top hosts)
  - [ ] Partnerships (Airbnb API ecosystem, property mgmt software)

### Pricing Strategy
- [ ] Commission (15-20%) vs SaaS ($49-199/mo) vs hybrid?
- [ ] What conversion rate is needed to be profitable?
- [ ] What's the willingness-to-pay? (survey)

## 📋 Checklist

- [ ] Interviewed 20+ Airbnb hosts (notes in RESEARCH.md)
- [ ] Validated pain point (80%+ agree on problem)
- [ ] Confirmed pricing willingness (60%+ would use at proposed price)
- [ ] Researched Airbnb/VRBO APIs (documented in RESEARCH.md)
- [ ] Got RentAHuman API access (tested search + booking)
- [ ] Identified target market (geography, property size, host type)
- [ ] Competitive analysis done (Vacasa, Evolve, alternatives)
- [ ] Unit economics validated (margin calculation)
- [ ] GTM strategy clear (first 10 customers, channels)
- [ ] Identified co-founders or advisors (Airbnb host community experts)

## 📝 Next Steps

1. **Week 0:** Complete this validation checklist
2. **Week 1:** Synthesize findings into RESEARCH.md
3. **Week 2:** Adjust plan based on validation
4. **Week 3:** Start development with confidence

---

**Status:** Pre-development (complete this first!)  
**Created:** 2026-02-22
