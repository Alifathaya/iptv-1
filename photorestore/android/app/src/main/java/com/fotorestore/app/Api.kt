package com.fotorestore.app

import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

data class EnhanceResp(val job_id: String, val status: String)
data class JobResp(val job_id: String, val status: String, val progress: Int,
                   val result_url: String? = null, val error: String? = null)

interface Api {
    @Multipart @POST("api/v1/enhance")
    suspend fun enhance(@Part file: MultipartBody.Part,
                        @Part("mode") mode: okhttp3.RequestBody,
                        @Part("strength") strength: okhttp3.RequestBody,
                        @Part("fidelity") fidelity: okhttp3.RequestBody): EnhanceResp
    @GET("api/v1/jobs/{id}") suspend fun job(@Path("id") id: String): JobResp
    @GET("api/v1/result/{id}") suspend fun result(@Path("id") id: String): ResponseBody
    @DELETE("api/v1/result/{id}") suspend fun delete(@Path("id") id: String): Map<String, Any>

    companion object {
        fun create(base: String): Api = Retrofit.Builder().baseUrl(base)
            .addConverterFactory(GsonConverterFactory.create()).build().create(Api::class.java)
    }
}
