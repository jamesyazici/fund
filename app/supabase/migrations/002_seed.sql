-- ============================================================
-- Demo seed data — development / staging only
-- Generates ~90 days of realistic NAV history and trades
-- ============================================================

-- ── Pods ─────────────────────────────────────────────────────

insert into pods (id, name, asset_class, description, benchmark_symbol, inception_date, starting_capital) values
  ('a1000000-0000-0000-0000-000000000001', 'Alpha Equities', 'equities',
   'Long/short US large-cap equity strategy focused on momentum and value factors.',
   'SPY', current_date - 90, 5000000),
  ('a1000000-0000-0000-0000-000000000002', 'Vol Arb', 'options',
   'Volatility arbitrage using equity options — primarily earnings and index plays.',
   'SPY', current_date - 90, 2500000),
  ('a1000000-0000-0000-0000-000000000003', 'Rates Pod', 'fixed_income',
   'Systematic fixed income strategy trading US Treasuries and investment-grade bonds.',
   'AGG', current_date - 90, 3000000);

-- ── Members ──────────────────────────────────────────────────

insert into members (pod_id, name, role) values
  ('a1000000-0000-0000-0000-000000000001', 'Jordan Kim',    'pm'),
  ('a1000000-0000-0000-0000-000000000001', 'Alex Chen',     'trader'),
  ('a1000000-0000-0000-0000-000000000001', 'Sam Rivera',    'trader'),

  ('a1000000-0000-0000-0000-000000000002', 'Morgan Lee',    'pm'),
  ('a1000000-0000-0000-0000-000000000002', 'Casey Torres',  'trader'),
  ('a1000000-0000-0000-0000-000000000002', 'Drew Patel',    'trader'),

  ('a1000000-0000-0000-0000-000000000003', 'Riley Johnson', 'pm'),
  ('a1000000-0000-0000-0000-000000000003', 'Quinn Murphy',  'trader');

-- ── NAV History (90 days, random-walk with drift) ─────────────
-- Uses generate_series to produce daily rows; each day's NAV drifts from previous.

do $$
declare
  v_date      date;
  v_pod_id    uuid;
  v_start     numeric;
  v_vol       numeric;
  v_nav       numeric;
  v_prev_nav  numeric;
  v_dr        numeric;
  v_rng       numeric;
  v_pod_ids   uuid[] := array[
    'a1000000-0000-0000-0000-000000000001'::uuid,
    'a1000000-0000-0000-0000-000000000002'::uuid,
    'a1000000-0000-0000-0000-000000000003'::uuid
  ];
  v_starts    numeric[] := array[5000000, 2500000, 3000000];
  v_vols      numeric[] := array[0.012, 0.018, 0.006];
  v_drifts    numeric[] := array[0.0004, 0.0003, 0.00015];
  i           int;
begin
  for i in 1..3 loop
    v_pod_id   := v_pod_ids[i];
    v_start    := v_starts[i];
    v_vol      := v_vols[i];
    v_prev_nav := v_start;

    for v_date in
      select gs::date
      from generate_series(current_date - 89, current_date, interval '1 day') gs
      where extract(dow from gs) not in (0, 6)   -- skip weekends
    loop
      v_rng := (random() * 2 - 1);
      v_dr  := v_drifts[i] + v_vol * v_rng;
      v_nav := v_prev_nav * (1 + v_dr);

      insert into nav_history (pod_id, date, nav, cash, daily_return)
      values (v_pod_id, v_date, round(v_nav, 2), round(v_nav * 0.05, 2), round(v_dr, 6))
      on conflict (pod_id, date) do nothing;

      v_prev_nav := v_nav;
    end loop;
  end loop;
end;
$$;

-- ── Positions ────────────────────────────────────────────────

insert into positions (pod_id, symbol, quantity, avg_entry_price, current_price, market_value, unrealized_pnl) values
  ('a1000000-0000-0000-0000-000000000001', 'AAPL',  500,   178.50, 184.20,   92100,   2850),
  ('a1000000-0000-0000-0000-000000000001', 'MSFT',  300,   410.00, 425.80,  127740,   4740),
  ('a1000000-0000-0000-0000-000000000001', 'NVDA',  200,   820.00, 875.50,  175100,  11100),
  ('a1000000-0000-0000-0000-000000000001', 'GOOGL', 100,  175.00, 180.90,   18090,     590),

  ('a1000000-0000-0000-0000-000000000002', 'SPY',    50,   490.00, 498.75,   24937.5,  437.5),
  ('a1000000-0000-0000-0000-000000000002', 'QQQ',    30,   420.00, 435.00,   13050,    450),

  ('a1000000-0000-0000-0000-000000000003', 'TLT',   400,    92.00,  94.50,   37800,   1000),
  ('a1000000-0000-0000-0000-000000000003', 'IEF',   600,    95.00,  96.80,   58080,   1080);

-- ── Sample trades (last 14 days) ─────────────────────────────

do $$
declare
  m1_pm     uuid; m1_t1 uuid; m1_t2 uuid;
  m2_pm     uuid; m2_t1 uuid; m2_t2 uuid;
  m3_pm     uuid; m3_t1 uuid;
  symbols1  text[] := array['AAPL','MSFT','NVDA','GOOGL','AMZN','META'];
  symbols2  text[] := array['SPY','QQQ','IWM'];
  symbols3  text[] := array['TLT','IEF','SHY','BND'];
  sides     text[] := array['buy','sell'];
  i         int;
  sym       text;
  side_val  text;
  qty       numeric;
  px        numeric;
  ts        timestamptz;
begin
  select id into m1_pm  from members where pod_id='a1000000-0000-0000-0000-000000000001' and role='pm'     limit 1;
  select id into m1_t1  from members where pod_id='a1000000-0000-0000-0000-000000000001' and role='trader' limit 1;
  select id into m1_t2  from members where pod_id='a1000000-0000-0000-0000-000000000001' and role='trader' offset 1 limit 1;
  select id into m2_pm  from members where pod_id='a1000000-0000-0000-0000-000000000002' and role='pm'     limit 1;
  select id into m2_t1  from members where pod_id='a1000000-0000-0000-0000-000000000002' and role='trader' limit 1;
  select id into m2_t2  from members where pod_id='a1000000-0000-0000-0000-000000000002' and role='trader' offset 1 limit 1;
  select id into m3_pm  from members where pod_id='a1000000-0000-0000-0000-000000000003' and role='pm'     limit 1;
  select id into m3_t1  from members where pod_id='a1000000-0000-0000-0000-000000000003' and role='trader' limit 1;

  for i in 1..40 loop
    sym      := symbols1[1 + (floor(random()*6))::int];
    side_val := sides[1 + (floor(random()*2))::int];
    qty      := (floor(random()*200)+10)::numeric;
    px       := (150 + random()*700)::numeric;
    ts       := now() - (random()*14 || ' days')::interval - (random()*8 || ' hours')::interval;
    insert into trades (pod_id, member_id, symbol, side, quantity, price, notional, asset_class, executed_at)
    values ('a1000000-0000-0000-0000-000000000001',
            (array[m1_pm,m1_t1,m1_t2])[1+(floor(random()*3))::int],
            sym, side_val, qty, round(px,2), round(qty*px,2), 'equities', ts);
  end loop;

  for i in 1..20 loop
    sym      := symbols2[1 + (floor(random()*3))::int];
    side_val := sides[1 + (floor(random()*2))::int];
    qty      := (floor(random()*50)+5)::numeric;
    px       := (400 + random()*150)::numeric;
    ts       := now() - (random()*14 || ' days')::interval - (random()*8 || ' hours')::interval;
    insert into trades (pod_id, member_id, symbol, side, quantity, price, notional, asset_class, executed_at)
    values ('a1000000-0000-0000-0000-000000000002',
            (array[m2_pm,m2_t1,m2_t2])[1+(floor(random()*3))::int],
            sym, side_val, qty, round(px,2), round(qty*px,2), 'options', ts);
  end loop;

  for i in 1..15 loop
    sym      := symbols3[1 + (floor(random()*4))::int];
    side_val := sides[1 + (floor(random()*2))::int];
    qty      := (floor(random()*300)+50)::numeric;
    px       := (88 + random()*20)::numeric;
    ts       := now() - (random()*14 || ' days')::interval - (random()*8 || ' hours')::interval;
    insert into trades (pod_id, member_id, symbol, side, quantity, price, notional, asset_class, executed_at)
    values ('a1000000-0000-0000-0000-000000000003',
            (array[m3_pm,m3_t1])[1+(floor(random()*2))::int],
            sym, side_val, qty, round(px,2), round(qty*px,2), 'fixed_income', ts);
  end loop;
end;
$$;

-- ── Seed metrics (approximate, computed from seeded NAV) ───────

insert into metrics (
  pod_id, as_of_date, cumulative_return, annualized_return, volatility,
  sharpe, sortino, beta, alpha, max_drawdown, calmar, var_95, win_rate, trade_count
)
select
  pod_id,
  max(date) as as_of_date,
  (exp(sum(ln(1 + coalesce(daily_return, 0)))) - 1)                     as cumulative_return,
  (exp(sum(ln(1 + coalesce(daily_return, 0))) * (252.0 / count(*))) - 1) as annualized_return,
  stddev_pop(daily_return) * sqrt(252)                                   as volatility,
  (avg(daily_return) - 0.05/252) / nullif(stddev_pop(daily_return),0) * sqrt(252) as sharpe,
  (avg(daily_return) - 0.05/252) / nullif(stddev_pop(case when daily_return < 0.05/252 then daily_return end),0) * sqrt(252) as sortino,
  0.85                                                                   as beta,
  0.032                                                                  as alpha,
  min(daily_return) * 5                                                  as max_drawdown,
  null                                                                   as calmar,
  percentile_cont(0.05) within group (order by daily_return)            as var_95,
  count(case when daily_return > 0 then 1 end)::numeric / count(*)       as win_rate,
  (select count(*) from trades t where t.pod_id = n.pod_id)::int        as trade_count
from nav_history n
where daily_return is not null
group by pod_id;
