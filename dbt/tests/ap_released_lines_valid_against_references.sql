-- Independent check of released allocation lines directly against the reference masters
-- (not against flags computed during enrichment): active CC, postable analytic accounts (no sub-accounts),
-- official crosswalk pair.
with cc as (
  select cost_center, min(active_flag) as active_flag from {{ source('raw','raw_ref_cost_centers') }} group by 1
), acct as (
  select account_code, min(accepts_posting) as accepts_posting from {{ source('raw','raw_ref_accounting_accounts') }} group by 1
), xwalk as (
  select distinct accounting_account, managerial_account from {{ source('raw','raw_ref_accounting_managerial_map') }}
), mgr as (
  select managerial_account, min(accepts_posting) as accepts_posting from {{ source('raw','raw_ref_managerial_accounts') }} group by 1
)
select r.id_externo_titulo, r.seq, r.centro_custo, r.conta_contabil, r.conta_gerencial
from {{ ref('ap_rateios') }} r
left join cc on cc.cost_center=r.centro_custo
left join acct a on a.account_code=r.conta_contabil
left join xwalk x on x.accounting_account=r.conta_contabil and x.managerial_account=r.conta_gerencial
left join mgr g on g.managerial_account=r.conta_gerencial
where cc.cost_center is null or upper(trim(cc.active_flag)) not in ('S','SIM','ATIVO','TRUE','1')
   or a.account_code is null or upper(trim(a.accepts_posting)) not in ('S','SIM','TRUE','1')
   or x.accounting_account is null
   or g.managerial_account is null or upper(trim(g.accepts_posting)) not in ('S','SIM','TRUE','1')
   or exists (select 1 from {{ source('raw','raw_ref_accounting_accounts') }} c where starts_with(trim(c.account_code), trim(r.conta_contabil) || '.'))
   or exists (select 1 from {{ source('raw','raw_ref_managerial_accounts') }} c where starts_with(trim(c.managerial_account), trim(r.conta_gerencial) || '.'))
