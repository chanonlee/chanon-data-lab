breed [stores store]
breed [material-batches material-batch]
breed [purchase-orders purchase-order]


; ============================================================
; GLOBALS
; ============================================================

globals [
  day
  total-waste
  total-tea-milk-tea
]


; ============================================================
; STORE
; ============================================================

stores-own [
  purchasing-policy

  ; 门店已经下单、但还没有到货的数量
  on-order-tea
  on-order-milk
  on-order-pearl

  ; 门店今天产生的采购请求
  request-tea
  request-milk
  request-pearl
]


; ============================================================
; MATERIAL BATCH
; ============================================================

material-batches-own [
  material-type
  quantity
  age
  shelf-life
]


; ============================================================
; PURCHASE ORDER
; ============================================================

purchase-orders-own [
  material-type
  quantity
  shelf-life
  arrival-day
]


; ============================================================
; SETUP
; ============================================================

to setup

  clear-all

  set day 0
  set total-waste 0
  set total-tea-milk-tea 0


  ; ----------------------------------------------------------
  ; 创建门店
  ; ----------------------------------------------------------

  create-stores 1 [

    setxy 0 0

    set shape "house"
    set color blue
    set size 2

    set purchasing-policy "reorder-point"

    set on-order-tea 0
    set on-order-milk 0
    set on-order-pearl 0

    set request-tea 0
    set request-milk 0
    set request-pearl 0
  ]


  ; ----------------------------------------------------------
  ; 初始库存
  ; ----------------------------------------------------------

  add-material "tea" 100 5
  add-material "milk" 80 3
  add-material "pearl" 50 2


  reset-ticks
end


; ============================================================
; MAIN LOOP
; ============================================================

to go

  set day day + 1


  ; ----------------------------------------------------------
  ; 1. 采购单到货
  ; ----------------------------------------------------------

  receive-purchase-orders


  ; ----------------------------------------------------------
  ; 2. Store 观察世界并做采购决策
  ; ----------------------------------------------------------

  ask stores [
    make-purchasing-decision
  ]


  ; ----------------------------------------------------------
  ; 3. 世界执行 Store 产生的采购请求
  ; ----------------------------------------------------------

  process-purchase-requests


  ; ----------------------------------------------------------
  ; 4. 根据配方自动生产奶茶
  ; ----------------------------------------------------------

  produce-milk-tea


  ; ----------------------------------------------------------
  ; 5. 一天结束，物料年龄 +1
  ; ----------------------------------------------------------

  ask material-batches [
    set age age + 1
  ]


  ; ----------------------------------------------------------
  ; 6. 过期报废
  ; ----------------------------------------------------------

  expire-materials


  tick
end


; ============================================================
; MATERIAL
; ============================================================

to add-material [material-name amount shelf]

  create-material-batches 1 [

    set material-type material-name
    set quantity amount
    set age 0
    set shelf-life shelf

    set shape "circle"
    set size 1

    place-near-store
    set-material-color
  ]
end


to place-near-store

  setxy
    (random-float 6) - 3
    (random-float 6) - 3
end


to set-material-color

  if material-type = "tea" [
    set color green
  ]

  if material-type = "milk" [
    set color white
  ]

  if material-type = "pearl" [
    set color brown
  ]
end


; ============================================================
; STORE BEHAVIOR
; ============================================================

to make-purchasing-decision

  ; ----------------------------------------------------------
  ; 门店观察：
  ;
  ; 有效库存 = 当前库存 + 在途库存
  ;
  ; 这样不会因为运输需要一天，而连续重复下单。
  ; ----------------------------------------------------------


  ; ==========================
  ; 牛奶
  ; ==========================

  let milk-available
    (total-material "milk") + on-order-milk

  if milk-available < 30 [

    set request-milk 100
  ]


  ; ==========================
  ; 珍珠
  ; ==========================

  let pearl-available
    (total-material "pearl") + on-order-pearl

  if pearl-available < 20 [

    set request-pearl 50
  ]


  ; ==========================
  ; 茶
  ; ==========================

  let tea-available
    (total-material "tea") + on-order-tea

  if tea-available < 50 [

    set request-tea 100
  ]
end


; ============================================================
; PURCHASE REQUEST
; ============================================================

; Store 自己不能 create-purchase-orders。
;
; 所以 Store 只产生“请求”：
;
; request-milk = 100
;
; 然后 Observer 在 process-purchase-requests 中
; 把请求转换成真正的 PurchaseOrder Agent。
;
; 这相当于：
;
; Agent 决策
;     ↓
; Intent / Command
;     ↓
; 世界执行
;


to process-purchase-requests

  ; Observer 遍历门店；create-purchase-orders 只能在 observer 上下文调用
  foreach sort stores [ the-store ->

    ; --------------------------------------------------------
    ; 牛奶
    ; --------------------------------------------------------

    let milk-req [request-milk] of the-store

    if milk-req > 0 [

      create-purchase-order
        "milk"
        milk-req
        3

      ask the-store [

        set on-order-milk
          on-order-milk + milk-req

        set request-milk 0
      ]
    ]


    ; --------------------------------------------------------
    ; 珍珠
    ; --------------------------------------------------------

    let pearl-req [request-pearl] of the-store

    if pearl-req > 0 [

      create-purchase-order
        "pearl"
        pearl-req
        2

      ask the-store [

        set on-order-pearl
          on-order-pearl + pearl-req

        set request-pearl 0
      ]
    ]


    ; --------------------------------------------------------
    ; 茶
    ; --------------------------------------------------------

    let tea-req [request-tea] of the-store

    if tea-req > 0 [

      create-purchase-order
        "tea"
        tea-req
        5

      ask the-store [

        set on-order-tea
          on-order-tea + tea-req

        set request-tea 0
      ]
    ]
  ]
end


; ============================================================
; PURCHASE ORDER
; ============================================================

to create-purchase-order [material-name amount shelf]

  create-purchase-orders 1 [

    set material-type material-name
    set quantity amount
    set shelf-life shelf

    ; 一天后到货
    set arrival-day day + 1

    set shape "square"
    set size 0.8
    set color yellow

    setxy
      (random-float 8) + 4
      (random-float 6) - 3
  ]
end


; ============================================================
; RECEIVE PURCHASE ORDERS
; ============================================================

to receive-purchase-orders

  ask purchase-orders with [
    arrival-day <= day
  ] [

    receive-purchase-order
  ]
end


; ============================================================
; PURCHASE ORDER BEHAVIOR
; ============================================================

to receive-purchase-order

  let material-name material-type
  let amount quantity
  let shelf shelf-life


  ; ----------------------------------------------------------
  ; 采购单到货
  ; ----------------------------------------------------------

  hatch-material-batches 1 [

    set material-type material-name
    set quantity amount
    set age 0
    set shelf-life shelf

    set shape "circle"
    set size 1

    place-near-store
    set-material-color
  ]


  ; ----------------------------------------------------------
  ; 通知门店：
  ; 在途库存减少
  ;
  ; 当前模型只有一个门店，因此直接 ask stores。
  ; 后面有多个门店时，把 store-id 加进 PurchaseOrder 即可。
  ; ----------------------------------------------------------

  ask one-of stores [

    if material-name = "tea" [
      set on-order-tea
        on-order-tea - amount
    ]

    if material-name = "milk" [
      set on-order-milk
        on-order-milk - amount
    ]

    if material-name = "pearl" [
      set on-order-pearl
        on-order-pearl - amount
    ]
  ]


  ; ----------------------------------------------------------
  ; 采购单完成
  ; ----------------------------------------------------------

  die
end


; ============================================================
; RECIPE
; ============================================================

; 珍珠奶茶：
;
; 茶      10
; 牛奶    20
; 珍珠    15
;
; 这里只定义规则，不把 Recipe 做成 Agent。
;


; ============================================================
; CALCULATE MAX PRODUCTION
; ============================================================

to-report max-milk-tea

  let tea-quantity
    total-material "tea"

  let milk-quantity
    total-material "milk"

  let pearl-quantity
    total-material "pearl"


  let tea-cups
    floor (tea-quantity / 10)

  let milk-cups
    floor (milk-quantity / 20)

  let pearl-cups
    floor (pearl-quantity / 15)


  report min (list
    tea-cups
    milk-cups
    pearl-cups
  )
end


; ============================================================
; PRODUCE MILK TEA
; ============================================================

to produce-milk-tea

  let amount max-milk-tea


  if amount <= 0 [
    stop
  ]


  ; ----------------------------------------------------------
  ; 消耗材料
  ; ----------------------------------------------------------

  consume-material
    "tea"
    (amount * 10)

  consume-material
    "milk"
    (amount * 20)

  consume-material
    "pearl"
    (amount * 15)


  ; ----------------------------------------------------------
  ; 记录生产量
  ; ----------------------------------------------------------

  set total-tea-milk-tea
    total-tea-milk-tea + amount
end


; ============================================================
; FEFO
; First Expired, First Out
; ============================================================

to consume-material [material-name amount]

  let remaining amount


  while [remaining > 0] [

    let candidates
      material-batches with [
        material-type = material-name
      ]


    if not any? candidates [
      stop
    ]


    ; --------------------------------------------------------
    ; 剩余保质期最短的批次优先
    ; --------------------------------------------------------

    let batch
      min-one-of candidates [
        shelf-life - age
      ]


    let batch-quantity
      [quantity] of batch


    ; --------------------------------------------------------
    ; 整个批次消耗
    ; --------------------------------------------------------

    ifelse batch-quantity <= remaining [

      set remaining
        remaining - batch-quantity

      ask batch [
        die
      ]
    ]


    ; --------------------------------------------------------
    ; 只消耗一部分
    ; --------------------------------------------------------

    [

      ask batch [
        set quantity
          quantity - remaining
      ]

      set remaining 0
    ]
  ]
end


; ============================================================
; EXPIRATION
; ============================================================

to expire-materials

  ask material-batches [

    if age >= shelf-life [

      set total-waste
        total-waste + quantity

      die
    ]
  ]
end


; ============================================================
; INVENTORY QUERY
; ============================================================

to-report total-material [material-name]

  report sum [
    quantity
  ] of material-batches with [
    material-type = material-name
  ]
end
@#$#@#$#@
GRAPHICS-WINDOW
280
10
649
399
-1
-1
11.0
1
10
1
1
1
0
1
1
1
-16
16
-16
16
1
1
1
ticks
30.0

BUTTON
15
15
88
48
NIL
setup
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
95
15
168
48
NIL
go
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
0

TEXTBOX
15
55
250
73
Milk Tea Inventory
14
0.0
1

MONITOR
15
85
90
130
day
day
0
1
11

MONITOR
95
85
195
130
produced
total-tea-milk-tea
0
1
11

MONITOR
200
85
295
130
waste
total-waste
0
1
11

MONITOR
15
140
90
185
tea
total-material "tea"
0
1
11

MONITOR
95
140
170
185
milk
total-material "milk"
0
1
11

MONITOR
175
140
250
185
pearl
total-material "pearl"
0
1
11

MONITOR
15
195
90
240
on-order-tea
[on-order-tea] of one-of stores
0
1
11

MONITOR
95
195
170
240
on-order-milk
[on-order-milk] of one-of stores
0
1
11

MONITOR
175
195
250
240
on-order-pearl
[on-order-pearl] of one-of stores
0
1
11

PLOT
15
255
295
420
Production and Waste
day
amount
0.0
10.0
0.0
10.0
true
true
"" ""
PENS
"produced" 1.0 0 -13345367 true "" "plot total-tea-milk-tea"
"waste" 1.0 0 -2674135 true "" "plot total-waste"

PLOT
310
255
620
420
Inventory
day
amount
0.0
10.0
0.0
10.0
true
true
"" ""
PENS
"tea" 1.0 0 -10899396 true "" "plot total-material \"tea\""
"milk" 1.0 0 -7500403 true "" "plot total-material \"milk\""
"pearl" 1.0 0 -6459832 true "" "plot total-material \"pearl\""
@#$#@#$#@
## WHAT IS IT?

This model simulates inventory, purchasing, production, and expiration for a milk-tea store.

Each day the store:
1. Receives arrived purchase orders
2. Decides whether to reorder using a reorder-point policy
3. Produces as many pearl milk teas as materials allow
4. Ages materials and scraps expired batches

## HOW IT WORKS

### Agents

- **store**: blue house. Observes inventory and creates purchase *requests* (intent). It does not create purchase-order agents directly.
- **material-batch**: circle. tea=green, milk=white, pearl=brown. Has quantity, age, shelf-life.
- **purchase-order**: yellow square. In-transit order; arrives next day as a material batch.

### Daily loop

1. Receive orders whose `arrival-day <= day`
2. Decide using effective inventory = on-hand + on-order
3. Observer converts requests into `purchase-order` agents
4. Produce using FEFO consumption
5. Age materials; scrap when `age >= shelf-life`

### Reorder points

| material | reorder point | order qty | shelf life |
|----------|---------------|-----------|------------|
| tea      | 50            | 100       | 5 days     |
| milk     | 30            | 100       | 3 days     |
| pearl    | 20            | 50        | 2 days     |

Lead time is fixed at **1 day**.

Recipe: tea 10 + milk 20 + pearl 15 = 1 cup.

### FEFO

Consume the batch with the smallest remaining life (`shelf-life - age`) first.

## HOW TO USE IT

1. Click **setup**
2. Click **go** to run day by day
3. Watch monitors and plots

## THINGS TO NOTICE

- Pearl expires fastest and often becomes the bottleneck.
- Counting on-order stock prevents repeated ordering during the 1-day lead time.
- The model produces the maximum feasible cups each day.

## THINGS TO TRY

- Change reorder points / order quantities in `make-purchasing-decision`
- Change `arrival-day` to lengthen lead time
- Change recipe amounts

## EXTENDING THE MODEL

- Multiple stores with `store-id` on purchase orders
- Stochastic daily demand instead of max production
- Use `purchasing-policy` to switch strategies
- BehaviorSpace experiments on reorder points

## NETLOGO FEATURES

- Multiple breeds for decision / stock / in-transit orders
- Agent intent then observer execution
- `min-one-of` for FEFO

## RELATED MODELS

Supply-chain and inventory models in the Models Library.

## CREDITS AND REFERENCES

Teaching example: Store decision -> purchase request -> PurchaseOrder -> MaterialBatch -> FEFO production and expiration.
@#$#@#$#@
default
true
0
Polygon -7500403 true true 150 5 40 250 150 205 260 250

airplane
true
0
Polygon -7500403 true true 150 0 135 15 120 60 120 105 15 165 15 195 120 180 135 240 105 270 120 285 150 270 180 285 210 270 165 240 180 180 285 195 285 165 180 105 180 60 165 15

arrow
true
0
Polygon -7500403 true true 150 0 0 150 105 150 105 293 195 293 195 150 300 150

box
false
0
Polygon -7500403 true true 150 285 285 225 285 75 150 135
Polygon -7500403 true true 150 135 15 75 150 15 285 75
Polygon -7500403 true true 15 75 15 225 150 285 150 135
Line -16777216 false 150 285 150 135
Line -16777216 false 150 135 15 75
Line -16777216 false 150 135 285 75

bug
true
0
Circle -7500403 true true 96 182 108
Circle -7500403 true true 110 127 80
Circle -7500403 true true 110 75 80
Line -7500403 true 150 100 80 30
Line -7500403 true 150 100 220 30

butterfly
true
0
Polygon -7500403 true true 150 165 209 199 225 225 225 255 195 270 165 255 150 240
Polygon -7500403 true true 150 165 89 198 75 225 75 255 105 270 135 255 150 240
Polygon -7500403 true true 139 148 100 105 55 90 25 90 10 105 10 135 25 180 40 195 85 194 139 163
Polygon -7500403 true true 162 150 200 105 245 90 275 90 290 105 290 135 275 180 260 195 215 195 162 165
Polygon -16777216 true false 150 255 135 225 120 150 135 120 150 105 165 120 180 150 165 225
Circle -16777216 true false 135 90 30
Line -16777216 false 150 105 195 60
Line -16777216 false 150 105 105 60

car
false
0
Polygon -7500403 true true 300 180 279 164 261 144 240 135 226 132 213 106 203 84 185 63 159 50 135 50 75 60 0 150 0 165 0 225 300 225 300 180
Circle -16777216 true false 180 180 90
Circle -16777216 true false 30 180 90
Polygon -16777216 true false 162 80 132 78 134 135 209 135 194 105 189 96 180 89
Circle -7500403 true true 47 195 58
Circle -7500403 true true 195 195 58

circle
false
0
Circle -7500403 true true 0 0 300

circle 2
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240

cow
false
0
Polygon -7500403 true true 200 193 197 249 179 249 177 196 166 187 140 189 93 191 78 179 72 211 49 209 48 181 37 149 25 120 25 89 45 72 103 84 179 75 198 76 252 64 272 81 293 103 285 121 255 121 242 118 224 167
Polygon -7500403 true true 73 210 86 251 62 249 48 208
Polygon -7500403 true true 25 114 16 195 9 204 23 213 25 200 39 123

cylinder
false
0
Circle -7500403 true true 0 0 300

dot
false
0
Circle -7500403 true true 90 90 120

face happy
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 255 90 239 62 213 47 191 67 179 90 203 109 218 150 225 192 218 210 203 227 181 251 194 236 217 212 240

face neutral
false
0
Circle -7500403 true true 8 7 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Rectangle -16777216 true false 60 195 240 225

face sad
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 168 90 184 62 210 47 232 67 244 90 220 109 205 150 198 192 205 210 220 227 242 251 229 236 206 212 183

fish
false
0
Polygon -1 true false 44 131 21 87 15 86 0 120 15 150 0 180 13 214 20 212 45 166
Polygon -1 true false 135 195 119 235 95 218 76 210 46 204 60 165
Polygon -1 true false 75 45 83 77 71 103 86 114 166 78 135 60
Polygon -7500403 true true 30 136 151 77 226 81 280 119 292 146 292 160 287 170 270 195 195 210 151 212 30 166
Circle -16777216 true false 215 106 30

flag
false
0
Rectangle -7500403 true true 60 15 75 300
Polygon -7500403 true true 90 150 270 90 90 30
Line -7500403 true 75 135 90 135
Line -7500403 true 75 45 90 45

flower
false
0
Polygon -10899396 true false 135 120 165 165 180 210 180 240 150 300 165 300 195 240 195 195 165 135
Circle -7500403 true true 85 132 38
Circle -7500403 true true 130 147 38
Circle -7500403 true true 192 85 38
Circle -7500403 true true 85 40 38
Circle -7500403 true true 177 40 38
Circle -7500403 true true 177 132 38
Circle -7500403 true true 70 85 38
Circle -7500403 true true 130 25 38
Circle -7500403 true true 96 51 108
Circle -16777216 true false 113 68 74
Polygon -10899396 true false 189 233 219 188 249 173 279 188 234 218
Polygon -10899396 true false 180 255 150 210 105 210 75 240 135 240

house
false
0
Rectangle -7500403 true true 45 120 255 285
Rectangle -16777216 true false 120 210 180 285
Polygon -7500403 true true 15 120 150 15 285 120
Line -16777216 false 30 120 270 120

leaf
false
0
Polygon -7500403 true true 150 210 135 195 120 210 60 210 30 195 60 180 60 165 15 135 30 120 15 105 40 104 45 90 60 90 90 105 105 120 120 120 105 60 120 60 135 30 150 15 165 30 180 60 195 60 180 120 195 120 210 105 240 90 255 90 263 104 285 105 270 120 285 135 240 165 240 180 270 195 240 210 180 210 165 195
Polygon -7500403 true true 135 195 135 240 120 255 105 255 105 285 135 285 165 240 165 195

line
true
0
Line -7500403 true 150 0 150 300

line half
true
0
Line -7500403 true 150 0 150 150

pentagon
false
0
Polygon -7500403 true true 150 15 15 120 60 285 240 285 285 120

person
false
0
Circle -7500403 true true 110 5 80
Polygon -7500403 true true 105 90 120 195 90 285 105 300 135 300 150 225 165 300 195 300 210 285 180 195 195 90
Rectangle -7500403 true true 127 79 172 94
Polygon -7500403 true true 195 90 240 150 225 180 165 105
Polygon -7500403 true true 105 90 60 150 75 180 135 105

plant
false
0
Rectangle -7500403 true true 135 90 165 300
Polygon -7500403 true true 135 255 90 210 45 195 75 255 135 285
Polygon -7500403 true true 165 255 210 210 255 195 225 255 165 285
Polygon -7500403 true true 135 180 90 135 45 120 75 180 135 210
Polygon -7500403 true true 165 180 165 210 225 180 255 120 210 135
Polygon -7500403 true true 135 105 90 60 45 45 75 105 135 135
Polygon -7500403 true true 165 105 165 135 225 105 255 45 210 60
Polygon -7500403 true true 135 90 120 45 150 15 180 45 165 90

square
false
0
Rectangle -7500403 true true 30 30 270 270

square 2
false
0
Rectangle -7500403 true true 30 30 270 270
Rectangle -16777216 true false 60 60 240 240

star
false
0
Polygon -7500403 true true 151 1 185 108 298 108 207 175 242 282 151 216 59 282 94 175 3 108 116 108

target
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240
Circle -7500403 true true 60 60 180
Circle -16777216 true false 90 90 120
Circle -7500403 true true 120 120 60

tree
false
0
Circle -7500403 true true 118 3 94
Rectangle -6459832 true false 120 195 180 300
Circle -7500403 true true 65 21 108
Circle -7500403 true true 116 41 127
Circle -7500403 true true 45 90 120
Circle -7500403 true true 104 74 152

triangle
false
0
Polygon -7500403 true true 150 30 15 255 285 255

triangle 2
false
0
Polygon -7500403 true true 150 30 15 255 285 255
Polygon -16777216 true false 151 99 225 223 75 224

truck
false
0
Rectangle -7500403 true true 4 45 195 187
Polygon -7500403 true true 296 193 296 150 259 134 244 104 208 104 207 194
Rectangle -1 true false 195 60 195 105
Polygon -16777216 true false 238 112 252 141 219 141 218 112
Circle -16777216 true false 234 174 42
Rectangle -7500403 true true 181 185 214 194
Circle -16777216 true false 144 174 42
Circle -16777216 true false 24 174 42
Circle -7500403 false true 24 174 42
Circle -7500403 false true 144 174 42
Circle -7500403 false true 234 174 42

turtle
true
0
Polygon -10899396 true false 215 204 240 233 246 254 228 266 215 252 193 210
Polygon -10899396 true false 195 90 225 75 245 75 260 89 269 108 261 124 240 105 225 105 210 105
Polygon -10899396 true false 105 90 75 75 55 75 40 89 31 108 39 124 60 105 75 105 90 105
Polygon -10899396 true false 132 85 134 64 107 51 108 17 150 2 192 18 192 52 169 65 172 87
Polygon -10899396 true false 85 204 60 233 54 254 72 266 85 252 107 210
Polygon -7500403 true true 119 75 179 75 209 101 224 135 220 225 175 261 128 261 81 224 74 135 88 99

wheel
false
0
Circle -7500403 true true 3 3 294
Circle -16777216 true false 30 30 240
Line -7500403 true 150 285 150 15
Line -7500403 true 15 150 285 150
Circle -7500403 true true 120 120 60
Line -7500403 true 216 40 79 269
Line -7500403 true 40 84 269 221
Line -7500403 true 40 216 269 79
Line -7500403 true 84 40 221 269

x
false
0
Polygon -7500403 true true 270 75 225 30 30 225 75 270
Polygon -7500403 true true 30 75 75 30 270 225 225 270
@#$#@#$#@
NetLogo 6.4.0
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
default
0.0
-0.2 0 0.0 1.0
0.0 1 1.0 0.0
0.2 0 0.0 1.0
link direction
true
0
Line -7500403 true 150 150 90 180
Line -7500403 true 150 150 210 180
@#$#@#$#@
1
@#$#@#$#@
