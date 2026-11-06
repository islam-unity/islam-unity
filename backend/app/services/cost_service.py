import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.config import settings
from app.db.base import utc_now
from app.db.models import AIModelPricing, SystemCurrencyConfig, AIUsageLog
from app.schemas.ai_chat import (
    TokenUsageDTO, ModelPricingDTO, CostConfigDTO,
    UpdateCostConfigRequest, UsageStatsDTO
)

logger = logging.getLogger(__name__)


class CostService:
    """
    Manages AI token usage tracking, pricing configuration, and cost calculations in USD and Iranian Rials (IRR).
    """

    @classmethod
    async def get_or_init_currency_config(cls, db: AsyncSession) -> SystemCurrencyConfig:
        cfg = await db.scalar(select(SystemCurrencyConfig).where(SystemCurrencyConfig.id == "primary_currency"))
        if not cfg:
            cfg = SystemCurrencyConfig(
                id="primary_currency",
                usd_to_irr_rate=settings.USD_TO_IRR_RATE,
                currency_name="IRR"
            )
            db.add(cfg)
            await db.commit()
            await db.refresh(cfg)
        return cfg

    @classmethod
    async def get_or_init_model_pricing(cls, db: AsyncSession, model_name: str) -> AIModelPricing:
        clean_name = model_name or settings.GEMINI_MODEL
        pricing = await db.scalar(select(AIModelPricing).where(AIModelPricing.model_name == clean_name))
        if not pricing:
            pricing = AIModelPricing(
                id=f"pricing_{clean_name}",
                model_name=clean_name,
                input_cost_per_million_usd=settings.DEFAULT_INPUT_COST_PER_M,
                output_cost_per_million_usd=settings.DEFAULT_OUTPUT_COST_PER_M,
                cached_cost_per_million_usd=settings.DEFAULT_CACHED_COST_PER_M,
                is_active=True
            )
            db.add(pricing)
            await db.commit()
            await db.refresh(pricing)
        return pricing

    @classmethod
    async def calculate_and_log_usage(
        cls,
        db: AsyncSession,
        user_id: Optional[str],
        conversation_id: Optional[str],
        message_id: Optional[str],
        model_name: str,
        prompt_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        latency_breakdown: Optional[Dict[str, float]] = None
    ) -> TokenUsageDTO:
        """
        Calculates exact cost for prompt tokens, output tokens, and cached tokens in both USD and IRR,
        then persists to ai_usage_logs table.
        """
        currency_cfg = await cls.get_or_init_currency_config(db)
        pricing = await cls.get_or_init_model_pricing(db, model_name)

        usd_rate = currency_cfg.usd_to_irr_rate or settings.USD_TO_IRR_RATE
        total_tokens = prompt_tokens + output_tokens + cached_tokens

        # Cost calculations per 1,000,000 tokens
        input_cost_usd = (prompt_tokens / 1_000_000.0) * pricing.input_cost_per_million_usd
        output_cost_usd = (output_tokens / 1_000_000.0) * pricing.output_cost_per_million_usd
        cached_cost_usd = (cached_tokens / 1_000_000.0) * pricing.cached_cost_per_million_usd

        cost_usd = round(input_cost_usd + output_cost_usd + cached_cost_usd, 7)
        cost_irr = round(cost_usd * usd_rate, 2)

        # Log into AIUsageLog
        log_id = f"usg_{uuid.uuid4().hex[:10]}"
        usage_log = AIUsageLog(
            id=log_id,
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            model_name=model_name or settings.GEMINI_MODEL,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            cost_irr=cost_irr,
            exchange_rate_applied=usd_rate,
            created_at=utc_now()
        )
        db.add(usage_log)
        await db.commit()

        return TokenUsageDTO(
            modelName=model_name,
            promptTokens=prompt_tokens,
            outputTokens=output_tokens,
            cachedTokens=cached_tokens,
            totalTokens=total_tokens,
            costUsd=cost_usd,
            costIrr=cost_irr,
            currency="IRR",
            latencyBreakdown=latency_breakdown
        )

    @classmethod
    async def get_cost_config(cls, db: AsyncSession) -> CostConfigDTO:
        currency_cfg = await cls.get_or_init_currency_config(db)
        pricings_res = await db.execute(select(AIModelPricing))
        pricings = pricings_res.scalars().all()

        if not pricings:
            default_p = await cls.get_or_init_model_pricing(db, settings.GEMINI_MODEL)
            pricings = [default_p]

        model_dtos = [
            ModelPricingDTO(
                modelName=p.model_name,
                inputCostPerMillionUsd=p.input_cost_per_million_usd,
                outputCostPerMillionUsd=p.output_cost_per_million_usd,
                cachedCostPerMillionUsd=p.cached_cost_per_million_usd,
                isActive=p.is_active
            ) for p in pricings
        ]

        return CostConfigDTO(
            usdToIrrRate=currency_cfg.usd_to_irr_rate,
            currencyName=currency_cfg.currency_name or "IRR",
            modelsPricing=model_dtos
        )

    @classmethod
    async def update_cost_config(cls, db: AsyncSession, data: UpdateCostConfigRequest) -> CostConfigDTO:
        currency_cfg = await cls.get_or_init_currency_config(db)
        if data.usdToIrrRate is not None and data.usdToIrrRate > 0:
            currency_cfg.usd_to_irr_rate = data.usdToIrrRate
        if data.currencyName:
            currency_cfg.currency_name = data.currencyName

        if data.modelsPricing:
            for p_req in data.modelsPricing:
                clean_name = p_req.modelName
                existing = await db.scalar(select(AIModelPricing).where(AIModelPricing.model_name == clean_name))
                if not existing:
                    existing = AIModelPricing(
                        id=f"pricing_{clean_name}",
                        model_name=clean_name
                    )
                    db.add(existing)

                existing.input_cost_per_million_usd = p_req.inputCostPerMillionUsd
                existing.output_cost_per_million_usd = p_req.outputCostPerMillionUsd
                existing.cached_cost_per_million_usd = p_req.cachedCostPerMillionUsd
                if p_req.isActive is not None:
                    existing.is_active = p_req.isActive

        await db.commit()
        return await cls.get_cost_config(db)

    @classmethod
    async def get_usage_statistics(
        cls,
        db: AsyncSession,
        conversation_id: Optional[str] = None
    ) -> UsageStatsDTO:
        currency_cfg = await cls.get_or_init_currency_config(db)

        stmt = select(
            func.count(AIUsageLog.id),
            func.coalesce(func.sum(AIUsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.output_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.cached_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.cost_usd), 0.0),
            func.coalesce(func.sum(AIUsageLog.cost_irr), 0.0)
        )
        if conversation_id:
            stmt = stmt.where(AIUsageLog.conversation_id == conversation_id)

        agg_res = await db.execute(stmt)
        row = agg_res.first()

        req_count, p_tokens, out_tokens, c_tokens, tot_tokens, c_usd, c_irr = (
            row[0], int(row[1]), int(row[2]), int(row[3]), int(row[4]), float(row[5]), float(row[6])
        )

        # Recent logs
        recent_stmt = select(AIUsageLog).order_by(desc(AIUsageLog.created_at)).limit(20)
        if conversation_id:
            recent_stmt = recent_stmt.where(AIUsageLog.conversation_id == conversation_id)

        logs_res = await db.execute(recent_stmt)
        logs = logs_res.scalars().all()

        recent_dtos = [
            {
                "id": l.id,
                "modelName": l.model_name,
                "conversationId": l.conversation_id,
                "promptTokens": l.prompt_tokens,
                "outputTokens": l.output_tokens,
                "cachedTokens": l.cached_tokens,
                "totalTokens": l.total_tokens,
                "costUsd": round(l.cost_usd, 6),
                "costIrr": round(l.cost_irr, 2),
                "timestamp": int(l.created_at.timestamp() * 1000)
            } for l in logs
        ]

        return UsageStatsDTO(
            totalRequests=req_count,
            totalPromptTokens=p_tokens,
            totalOutputTokens=out_tokens,
            totalCachedTokens=c_tokens,
            totalTokens=tot_tokens,
            totalCostUsd=round(c_usd, 6),
            totalCostIrr=round(c_irr, 2),
            usdToIrrRate=currency_cfg.usd_to_irr_rate,
            recentLogs=recent_dtos
        )
