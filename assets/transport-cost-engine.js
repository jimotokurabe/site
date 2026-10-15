/* Scenario arithmetic only; qualifications and current entitlements are not inferred. */
(function(root){'use strict';
function estimate(rule,fare,trips){
 if(!rule||!Number.isInteger(fare)||!Number.isInteger(trips)||fare<0||fare>100000||trips<1||trips>100)return null;
 if(!['coupon','percent','fixed'].includes(rule.kind))return null;
 if(rule.kind==='coupon'&&(!Number.isInteger(rule.stock)||rule.stock<0||!(rule.face>0)||!(rule.cap>0)))return null;
 if(rule.kind==='percent'&&!(rule.percent>=0&&rule.percent<=100))return null;
 if(rule.kind==='fixed'&&!(rule.fixedFare>=0))return null;
 const rides=trips*2,normal=fare*rides,months=[];let remaining=rule.stock||0;
 for(let month=1;month<=12;month++){
  let net=0,used=0,couponSaving=0,discountSaving=0;
  for(let i=0;i<rides;i++){
   if(rule.kind==='fixed'){net+=rule.fixedFare;discountSaving+=fare-rule.fixedFare;continue;}
   if(rule.kind==='percent'){const payment=Math.ceil(fare*(100-rule.percent)/100);net+=payment;discountSaving+=fare-payment;continue;}
   const discounted=Math.ceil(fare*(100-(rule.baseDiscount||0))/100);discountSaving+=fare-discounted;
   let allowed=rule.rounding==='floor'?Math.floor(discounted/rule.face):Math.ceil(discounted/rule.face);
   if(rule.tier==='sanda')allowed=discounted<2000?1:discounted<3000?2:3;
   if(rule.tier==='inami')allowed=discounted<1000?1:discounted<1500?2:3;
   const count=Math.min(rule.cap,remaining,allowed),subsidy=Math.min(discounted,count*rule.face);
   remaining-=count;used+=count;couponSaving+=subsidy;net+=discounted-subsidy;
  }
  const fee=month===1?(rule.annualFee||0):0;net+=fee;
  months.push({month,normal,net,saved:normal-net,used,remaining,couponSaving,discountSaving,fee});
 }
 return {months,total:months.reduce((n,m)=>n+m.net,0),normal:normal*12,saved:months.reduce((n,m)=>n+m.saved,0),used:months.reduce((n,m)=>n+m.used,0),remaining};
}
if(typeof module!=='undefined')module.exports={estimate};else root.TransportCost={estimate};
})(typeof window!=='undefined'?window:globalThis);
