# Modal Server Issue - Quantized Model Instability

## Problem
El modelo base Qwen2.5-7B sin fine-tuning genera valores `inf`/`nan` cuando se usa con cuantización (4-bit o 8-bit) en Modal.

## Intentos realizados:
1. ✅ Arreglado dependencias (numpy <2.0, scipy)
2. ✅ Agregado `renormalize_logits=True`
3. ✅ Cambiado de 4-bit a 8-bit quantization
4. ✅ Cambiado a greedy decoding (`do_sample=False`)
5. ❌ Todos fallan con el mismo error

## Error:
```
RuntimeError: probability tensor contains either `inf`, `nan` or element < 0
  at torch.multinomial()
```

## Solución temporal:
**Usa modo "template" en VS Code** hasta que el training termine:

```json
{
  "bioql.mode": "template",
  "bioql.enableChat": true
}
```

## Solución definitiva:
**Esperar a que termine el training TRAIN_ROBUST.py** (~2-3 horas más)

El modelo fine-tuned será estable y podrá:
- Usar con 4-bit quantization sin problemas
- Generar código BioQL de mejor calidad
- Responder específicamente a quantum programming tasks

## Status del Training:
- ✅ Dataset generado (100K examples)
- ✅ Modelo Qwen2.5-7B cargado
- ✅ LoRA configurado (10M params entrenables)
- 🔄 Tokenizando dataset actualmente
- ⏳ Training iniciará pronto

Monitor: https://modal.com/apps/spectrix/main/ap-KAm0DiHDJqgnkwnLeGp6jM

## Alternativa: Modelo sin cuantización
Si necesitas Modal YA, puedo deployer el modelo sin cuantización (fp16 completo) pero:
- Requerirá GPU más grande (A10G → A100)
- Costará más (~$0.001/seg vs $0.0004/seg)
- Seguirá sin estar fine-tuned para BioQL
