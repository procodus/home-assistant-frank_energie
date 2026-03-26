[![Latest Release](https://img.shields.io/github/v/release/procodus/home-assistant-frank_energie?label=Version)](https://github.com/procodus/home-assistant-frank_energie/releases/)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

# Frank Energie Custom Component for Home Assistant

This integration exposes real-time electricity and gas pricing from [Frank Energie](https://www.frankenergie.nl/) as sensors in Home Assistant.

Use the sensor values to automate devices based on current energy prices — for example, run appliances when prices are low.

## Requirements

- Home Assistant **2026.3.0** or newer

## Installation

### HACS (recommended)

Add this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS with category **Integration**, then install it.

### Manual

Copy the `custom_components/frank_energie` folder into the `custom_components` directory of your Home Assistant installation and restart.

## Configuration

<a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=frank_energie" target="_blank">
    <img src="https://my.home-assistant.io/badges/config_flow_start.svg">
</a>

Add the integration via **Settings > Devices & Services > Add Integration > Frank Energie**.

### Authentication (optional)

During setup you can choose to log in with your Frank Energie account. Login is **not required** — without it you still get all public price sensors. Logging in additionally provides:

- Personalized prices (with your contract markups)
- Monthly cost sensors (actual and expected)
- Invoice sensors (previous, current, upcoming period)

## Sensors

### Price sensors (enabled by default)

| Sensor | Unit | Description |
|--------|------|-------------|
| Current electricity price (All-in) | EUR/kWh | Total price including all taxes and markups |
| Current electricity market price | EUR/kWh | Market price only |
| Current electricity price including tax | EUR/kWh | Market price + tax |
| Current gas price (All-in) | EUR/m3 | Total gas price |
| Current gas market price | EUR/m3 | Market price only |
| Current gas price including tax | EUR/m3 | Market price + tax |
| Lowest energy price today | EUR/kWh | Lowest electricity price of the day |
| Highest energy price today | EUR/kWh | Highest electricity price of the day |
| Average electricity price today | EUR/kWh | Average electricity price of the day |
| Lowest gas price today | EUR/m3 | Lowest gas price of the day |
| Highest gas price today | EUR/m3 | Highest gas price of the day |

### Price sensors (disabled by default)

| Sensor | Unit | Description |
|--------|------|-------------|
| Current electricity VAT price | EUR/kWh | VAT component |
| Current electricity sourcing markup | EUR/kWh | Sourcing markup component |
| Current electricity tax only | EUR/kWh | Energy tax component |
| Current gas VAT price | EUR/m3 | VAT component |
| Current gas sourcing price | EUR/m3 | Sourcing markup component |
| Current gas tax only | EUR/m3 | Energy tax component |

### Cost sensors (authenticated only)

| Sensor | Unit | Description |
|--------|------|-------------|
| Actual monthly cost | EUR | Actual costs until last meter reading |
| Expected monthly cost until now | EUR | Expected costs until last meter reading |
| Invoice previous period | EUR | Previous period invoice amount |
| Invoice current period | EUR | Current period invoice amount |
| Invoice upcoming period | EUR | Upcoming period invoice amount |

## Template examples

Several sensors include a `prices` attribute containing all known hourly prices. Use Jinja2 templates to create custom sensors.

**Highest upcoming price:**
```jinja
{{ state_attr('sensor.current_electricity_price_all_in', 'prices')
   | selectattr('from', 'gt', now())
   | max(attribute='price') }}
```

**Lowest price today:**
```jinja
{{ state_attr('sensor.current_electricity_price_all_in', 'prices')
   | selectattr('till', 'le', now().replace(hour=23))
   | min(attribute='price') }}
```

**Lowest price in the next 6 hours:**
```jinja
{{ state_attr('sensor.current_electricity_price_all_in', 'prices')
   | selectattr('from', 'gt', now())
   | selectattr('till', 'lt', now() + timedelta(hours=6))
   | min(attribute='price') }}
```

## Chart examples

Using [ApexCharts Card](https://github.com/RomRider/apexcharts-card) you can plot the hourly prices.

### 48-hour overview

![48-hour chart](/images/example_1.png)

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
now:
  show: true
  label: Now
header:
  show: true
  title: Energy price per hour (EUR/kWh)
series:
  - entity: sensor.current_electricity_price_all_in
    show:
      legend_value: false
    stroke_width: 2
    float_precision: 3
    type: column
    opacity: 0.3
    color: '#03b2cb'
    data_generator: |
      return entity.attributes.prices.map((record, index) => {
        return [record.from, record.price];
      });
```

### Upcoming 10 hours

![Upcoming hours chart](/images/example_2.png)

```yaml
type: custom:apexcharts-card
graph_span: 14h
span:
  start: hour
  offset: '-3h'
now:
  show: true
  label: Now
header:
  show: true
  show_states: true
  colorize_states: true
yaxis:
  - decimals: 2
    min: 0
    max: '|+0.10|'
series:
  - entity: sensor.current_electricity_price_all_in
    show:
      in_header: raw
      legend_value: false
    stroke_width: 2
    float_precision: 4
    type: column
    opacity: 0.3
    color: '#03b2cb'
    data_generator: |
      return entity.attributes.prices.map((record, index) => {
        return [record.from, record.price];
      });
```
